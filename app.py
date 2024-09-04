from flask import Flask, redirect, request, jsonify
from pymongo import MongoClient
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

APP_ID = os.getenv('APP_ID')
SECRET_KEY = os.getenv('MERCADOLIBRE_SECRET_KEY')
REDIRECT_URI = os.getenv('REDIRECT_URI')
DASHBOARD_URI = os.getenv('DASHBOARD_URI')

mongo = MongoClient(os.getenv('MONGO_URI'))
db = mongo[os.getenv('DATABASE_NAME')]
inmobiliary_collection = db[os.getenv('INMOBILIARY_COLLECTION')]
publicaciones_collection = db[os.getenv('PUBLICATIONS_COLLECTION')]

def chequear_mercadolibre(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://api.mercadolibre.com/sites", headers=headers)
    return response.status_code == 200

def sincronizar_publicaciones(inmobiliary_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    
    # Obtener publicaciones de MercadoLibre
    response = requests.get("https://api.mercadolibre.com/users/me/items/search", headers=headers)
    if response.status_code != 200:
        raise Exception("Error al obtener las publicaciones desde MercadoLibre")
    
    publicaciones_ml = response.json().get("results", [])
    
    for publicacion_id in publicaciones_ml:
        ml_publicacion = requests.get(f"https://api.mercadolibre.com/items/{publicacion_id}", headers=headers).json()
        
        # Actualizar o insertar la publicación en la base de datos con usuario_nulo
        publicaciones_collection.update_one(
            {"_id": publicacion_id},
            {"$set": {
                "inmobiliary_id": inmobiliary_id,
                "user_id": None,  # Asociar a usuario nulo inicialmente
                **ml_publicacion  # Cargar toda la informacion de la publicacion
            }},
            upsert=True
        )

@app.route('/asociar_usuario/<publicacion_id>/<user_id>', methods=['PUT'])
def asociar_usuario(publicacion_id, user_id):
    # Actualizar la publicación en la base de datos
    result = publicaciones_collection.update_one(
        {"_id": publicacion_id},
        {"$set": {"user_id": user_id}}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Publicación no encontrada"}), 404
    
    return jsonify({"message": "Publicación actualizada correctamente"}), 200


@app.route('/mercadolibre/<inmobiliary_id>', methods=['GET'])
def login(inmobiliary_id):
    auth_url = f"https://auth.mercadolibre.com/authorization?response_type=code&client_id={APP_ID}&redirect_uri={REDIRECT_URI}&state={inmobiliary_id}"
    return jsonify({"auth_url": auth_url})

@app.route('/callback', methods=['GET'])
def callback():
    code = request.args.get('code')
    inmobiliary_id = request.args.get('state')  # Usar state para obtener el ID de la inmobiliaria

    if not code or not inmobiliary_id:
        # Redirigir con un mensaje de error si falta el código o el ID de la inmobiliaria
        return redirect(f'{DASHBOARD_URI}?status=error&message=Missing+code+or+state')

    response = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": APP_ID,
            "client_secret": SECRET_KEY,
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
    )

    if response.status_code != 200:
        # Redirigir con un mensaje de error si falla la obtención del token
        return redirect(f'{DASHBOARD_URI}?status=error&message=Failed+to+obtain+access+token')

    token_info = response.json()
    
    inmobiliary_collection.update_one(
        {"_id": inmobiliary_id},
        {"$set": {"mercadolibre_token": token_info['access_token']}},
        upsert=True
    )

    try:
        # Sincronización inicial
        sincronizar_publicaciones(inmobiliary_id, token_info['access_token'])
    except Exception as e:
        # Redirigir con un mensaje de error si falla la sincronización
        return redirect(f'{DASHBOARD_URI}?status=error&message=Synchronization+failed:+{str(e)}')

    # Redirigir con un mensaje de éxito
    return redirect(f'{DASHBOARD_URI}?status=success&message=Authenticated+and+synchronized+successfully')

@app.route('/desvincular/<inmobiliary_id>', methods=['POST'])
def desvincular_mercadolibre(inmobiliary_id):
    inmobiliaria = inmobiliary_collection.find_one({"_id": inmobiliary_id})
    if not inmobiliaria:
        return jsonify({"error": "Inmobiliaria no encontrada"}), 404
    
    # Eliminar el token de MercadoLibre y marcar como no vinculado
    inmobiliary_collection.update_one(
        {"_id": inmobiliary_id},
        {"$unset": {"mercadolibre_token": "", "mercadolibre_user_id": ""}}
    )
    
    return jsonify({"message": "Inmobiliaria desvinculada de MercadoLibre con éxito"}), 200

@app.route('/chequear_vinculacion/<inmobiliary_id>', methods=['GET'])
def chequear_vinculacion(inmobiliary_id):
    inmobiliaria = inmobiliary_collection.find_one({"_id": inmobiliary_id})
    if not inmobiliaria:
        return jsonify({"error": "Inmobiliaria no encontrada"}), 404
    
    if 'mercadolibre_token' not in inmobiliaria:
        return jsonify({"vinculado": False, "message": "Inmobiliaria no vinculada con MercadoLibre"}), 404
    
    return jsonify({"vinculado": True, "message": "Inmobiliaria vinculada con MercadoLibre"}), 200


@app.route('/<inmobiliary_id>/<user_id>', methods=['POST'])
def crear_publicacion(inmobiliary_id, user_id):
    inmobiliaria = inmobiliary_collection.find_one({"_id": inmobiliary_id})
    if not inmobiliaria or 'mercadolibre_token' not in inmobiliaria:
        return jsonify({"error": "Inmobiliaria no vinculada con MercadoLibre"}), 400
    
    if not chequear_mercadolibre(inmobiliaria['mercadolibre_token']):
        return jsonify({"error": "MercadoLibre no está operativo en este momento"}), 503
    
    headers = {"Authorization": f"Bearer {inmobiliaria['mercadolibre_token']}"}
    publicacion = request.json
    response = requests.post("https://api.mercadolibre.com/items", json=publicacion, headers=headers)
    ml_publication_id = response.json().get("id")  # ID devuelta por MercadoLibre
    
    publicaciones_collection.update_one(
        {"_id": ml_publication_id},
        {"$set": {
            "inmobiliary_id": inmobiliary_id,
            "user_id": user_id,
            **publicacion
        }},
        upsert=True
    )
    return jsonify({"message": "Publicacion creada y sincronizada con MercadoLibre"}), 201

@app.route('/<publicacion_id>', methods=['PUT'])
def modificar_publicacion(publicacion_id):
    publicacion = publicaciones_collection.find_one({"_id": publicacion_id})

    if not publicacion:
        return jsonify({"error": "Publication not found"}), 404

    inmobiliaria = inmobiliary_collection.find_one({"_id": publicacion["inmobiliary_id"]})

    if not inmobiliaria or 'mercadolibre_token' not in inmobiliaria:
        return jsonify({"error": "Inmobiliaria no vinculada con MercadoLibre"}), 400
    
    if not chequear_mercadolibre(inmobiliaria['mercadolibre_token']):
        return jsonify({"error": "MercadoLibre no está operativo en este momento"}), 503
    
    publicacion = request.json
    
    headers = {"Authorization": f"Bearer {inmobiliaria['mercadolibre_token']}"}
    response = requests.put(f"https://api.mercadolibre.com/items/{publicacion_id}", json=publicacion, headers=headers)
    
    if response.status_code == 200:
        publicaciones_collection.update_one(
            {"_id": publicacion_id},
            {"$set": publicacion}  # Actualiza toda la publicación con los datos recibidos
        )
    
    return jsonify(response.json()), response.status_code

@app.route('/<publicacion_id>', methods=['DELETE'])
def borrar_publicacion(publicacion_id):
    publicacion = publicaciones_collection.find_one({"_id": publicacion_id})
    if not publicacion:
        return jsonify({"error": "Publicación no encontrada"}), 404
    
    inmobiliaria = inmobiliary_collection.find_one({"_id": publicacion["inmobiliary_id"]})
    if not inmobiliaria or 'mercadolibre_token' not in inmobiliaria:
        return jsonify({"error": "Inmobiliaria no vinculada con MercadoLibre"}), 400
    
    if not chequear_mercadolibre(inmobiliaria['mercadolibre_token']):
        return jsonify({"error": "MercadoLibre no está operativo en este momento"}), 503
    
    headers = {"Authorization": f"Bearer {inmobiliaria['mercadolibre_token']}"}
    response = requests.delete(f"https://api.mercadolibre.com/items/{publicacion_id}", headers=headers)
    
    if response.status_code == 200:
        publicaciones_collection.delete_one({"_id": publicacion_id})
    
    return jsonify({"message": "Publicacion eliminada en MercadoLibre y en la base de datos"}), 200

@app.route('/inmobiliaria/<inmobiliary_id>', methods=['GET'])
def obtener_publicaciones_inmobiliaria(inmobiliary_id):
    # Buscar todas las publicaciones asociadas a la inmobiliaria
    publicaciones = publicaciones_collection.find({"inmobiliary_id": inmobiliary_id})
    publicaciones_list = list(publicaciones)
    
    # Formatear las publicaciones para excluir el campo _id de MongoDB
    publicaciones_formateadas = [
        {
            "id": pub.get("_id"),
            "inmobiliaria": pub.get("inmobiliary_id"),
            "usuario": pub.get("user_id"),
            **{k: v for k, v in pub.items() if k not in ["_id", "inmobiliary_id", "user_id"]}
        }
        for pub in publicaciones_list
    ]
    
    return jsonify(publicaciones_formateadas), 200

@app.route('/usuario/<user_id>', methods=['GET'])
def obtener_publicaciones_usuario(user_id):
    # Buscar todas las publicaciones asociadas al usuario
    publicaciones = publicaciones_collection.find({"user_id": user_id})
    publicaciones_list = list(publicaciones)
    
    # Formatear las publicaciones para excluir el campo _id de MongoDB
    publicaciones_formateadas = [
        {
            "id": pub.get("_id"),
            "inmobiliaria": pub.get("inmobiliary_id"),
            "usuario": pub.get("user_id"),
            **{k: v for k, v in pub.items() if k not in ["_id", "inmobiliary_id", "user_id"]}
        }
        for pub in publicaciones_list
    ]
    
    return jsonify(publicaciones_formateadas), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
