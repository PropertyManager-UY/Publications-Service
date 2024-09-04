# Servicio de Publicaciones

Este repositorio contiene el código fuente y los archivos necesarios para desplegar y ejecutar un servicio de gestión de publicaciones en un clúster de Kubernetes.

## Descripción

El servicio de publicaciones se dedica a la gestión de datos de publicaciones, permitiendo la creación, actualización, eliminación y consulta de publicaciones para inmobiliarias. Este servicio facilita la sincronización y gestión de publicaciones en MercadoLibre.

## Índice

- [Proceso de Despliegue](#proceso-de-despliegue)
- [Uso del Servicio](#uso-del-servicio)
  - [Funcionalidades Principales](#funcionalidades-principales)
    - [Hacer la solicitud a MercadoLibre para vincularse](#hacer-la-solicitud-a-mercadolibre-para-vincularse)
    - [Recibir y procesar vínculo de MercadoLibre](#recibir-y-procesar-vinculo-de-mercadolibre)
    - [Verificar vinculación](#verificar-vinculacion)
    - [Desvincular Inmobiliaria de MercadoLibre](#desvincular-inmobiliaria-de-mercadolibre)
    - [Asociar un Usuario a una Publicación](#asociar-un-usuario-a-una-publicacion)
    - [Creación de Publicación](#creación-de-publicación)
    - [Actualización de Publicación](#actualización-de-publicación)
    - [Eliminación de Publicación](#eliminación-de-publicación)
    - [Obtener Publicaciones de Inmobiliaria](#obtener-publicaciones-de-inmobiliaria)
    - [Obtener Publicaciones de Usuario](#obtener-publicaciones-de-usuario)
- [Versiones Disponibles](#versiones-disponibles)
- [Contribución](#contribución)

## Proceso de Despliegue

Para desplegar el servicio de publicaciones en un clúster de Kubernetes, sigue los siguientes pasos:

1. **Configuración de Secrets para el servicio:** Crea un Secret en el clúster que contenga los siguientes datos:
   - `PUBLICATIONS_COLLECTION`: Nombre para la colección de publicaciones dentro de la base de datos de MongoDB.
   - `INMOBILIARY_COLLECTION`: Nombre para la colección de inmobiliarias dentro de la base de datos de MongoDB.
   - `DATABASE_NAME`: Nombre para la base de datos del proyecto.
   - `MONGO_URI`: URL del servidor de DB dentro del clúster.
   - `APP_ID`: ID de la aplicación de MercadoLibre.
   - `MERCADOLIBRE_SECRET_KEY`: Clave secreta de la aplicación de MercadoLibre.
   - `REDIRECT_URI`: URI de redirección después de la autenticación con MercadoLibre.
   - `DASHBOARD_URI`: URI del panel de control para redirigir después de la autenticación.

2. **Configuración de Variables de Entorno:** Define las siguientes variables de entorno en tu flujo de trabajo de GitHub Actions o en tu entorno local:
   - `DOCKER_USERNAME`: Nombre de usuario de Docker Hub.
   - `DOCKER_PASSWORD`: Contraseña de Docker Hub.
   - `K8_NAMESPACE`: Nombre del namespace de Kubernetes donde se desplegará el servicio.
   - `K8_DEPLOYMENT`: Nombre del deployment de Kubernetes.
   - `K8_SECRET`: Nombre del secret donde se encuentran los datos del clúster.
   - `HPA_NAME`: Nombre del HPA (Horizontal Pod Autoscaler).
   - `SERVICE_NAME`: Nombre del servicio de Kubernetes.
   - `K8_APP`: Nombre de la aplicación.

3. **Ejecución del Flujo de Trabajo:** Ejecuta el flujo de trabajo de GitHub Actions `deploy.yml`. Este flujo de trabajo construirá la imagen del contenedor, la subirá a Docker Hub y luego aplicará los recursos de Kubernetes necesarios en el clúster.

4. **Verificación del Despliegue:** Una vez completado el flujo de trabajo, verifica que el servicio de publicaciones esté desplegado correctamente en tu clúster de Kubernetes.

## Uso del Servicio

El Servicio de Gestión de Publicaciones es una API RESTful diseñada para manejar la creación, actualización, eliminación y consulta de publicaciones. Este servicio está construido utilizando Flask y MongoDB para la persistencia de datos, y está integrado con MercadoLibre para la sincronización automática.

### Funcionalidades Principales:

#### Hacer la solicitud a mercadolibre para vincularse

- **Ruta**: /mercadolibre/<inmobiliary_id>
- **Método**: GET
- **Descripción**: Genera la URL de autenticación para vincular una cuenta de MercadoLibre con la inmobiliaria.
- **Salida Exitosa (200):**
```json
{
    "auth_url": "https://auth.mercadolibre.com/authorization?response_type=code&client_id=<APP_ID>&redirect_uri=<REDIRECT_URI>&state=<inmobiliary_id>"
}
```

#### Recibir y procesar vinculo de mercadolibre

- **Ruta**: /callback
- **Método**: GET
- **Descripción**: Recibe el código de autorización de MercadoLibre y lo utiliza para obtener un token de acceso.
- **Salida Exitosa (Redirección a Dashboard):**
```
Redirección a: <DASHBOARD_URI>?status=success&message=Authenticated+and+synchronized+successfully
```
- **Salida de Error (Redirección a Dashboard):**
```
Redirección a: <DASHBOARD_URI>?status=error&message=Failed+to+obtain+access+token
```

#### Verificar vinculacion

- **Ruta**: /chequear_vinculacion/<inmobiliary_id>
- **Método**: GET
- **Descripción**: Verifica si una inmobiliaria está vinculada a MercadoLibre.
- **Salida Exitosa (200):**
```json
{
    "vinculado": true,
    "message": "Inmobiliaria vinculada con MercadoLibre"
}
```
- **Salida de Error (404):**
```json
{
    "vinculado": false,
    "message": "Inmobiliaria no vinculada con MercadoLibre"
}
```

#### Desvincular Inmobiliaria de Mercadolibre

- **Ruta**: /desvincular/<inmobiliary_id>
- **Método**: POST
- **Descripción**: Desvincula la cuenta de MercadoLibre de una inmobiliaria específica.
- **Salida Exitosa (200):**
```json
{
    "message": "Inmobiliaria desvinculada de MercadoLibre con éxito"
}
```
- **Salida de Error (404):**
```json
{
    "error": "Inmobiliaria no encontrada"
}
```

#### Asociar un Usuario a una publicacion

- **Ruta**: /asociar_usuario/<publicacion_id>/<user_id>
- **Método**: PUT
- **Descripción**: Cambia o asocia un usuario a una publicacion ya existente en la base de datos.
- **Salida Exitosa (200):**
```json
{
    "message": "Publicación actualizada correctamente"
}
```
- **Salida de Error (404):**
```json
{
    "error": "Publicación no encontrada"
}
```

#### Creación de Publicación

- **Ruta**: /<inmobiliary_id>/<user_id>
- **Método**: POST
- **Descripción**: Crea una nueva publicación en MercadoLibre y la sincroniza con la base de datos local.
- **Datos del Request:**
```json
{
    "title": "Casa en venta",
    "category_id": "MLU12345",
    "price": 100000,
    "currency_id": "USD",
    "available_quantity": 1,
    "buying_mode": "buy_it_now",
    "listing_type_id": "gold_special",
    "condition": "new",
    "description": {
        "plain_text": "Hermosa casa en venta en excelente ubicación."
    },
    "pictures": [
        {"source": "https://example.com/imagen1.jpg"},
        {"source": "https://example.com/imagen2.jpg"}
    ]
}
```
- **Salida Exitosa (201):**
```json
{
    "message": "Publicacion creada y sincronizada con MercadoLibre"
}
```
- **Salida de Error (400):**
```json
{
    "error": "Inmobiliaria no vinculada con MercadoLibre"
}
```
- **Salida de Error (503):**
```json
{
    "error": "MercadoLibre no está operativo en este momento"
}
```

#### Actualización de Publicación

- **Ruta**: /<publicacion_id>
- **Método**: PUT
- **Descripción**: Modifica una publicación existente en MercadoLibre y en la base de datos.
- **Datos del Request:**
```json
{
    "title": "Casa en venta - Actualizada",
    "price": 95000,
    "available_quantity": 2
}
```
- **Salida Exitosa (200):**
```json
{
    "id": "MLU987654321",
    "title": "Casa en venta - Actualizada",
    "price": 95000,
    "currency_id": "USD",
    "available_quantity": 2,
    ...
}
```
- **Salida de Error (404):**
```json
{
    "error": "Publication not found"
}
```
- **Salida de Error (400):**
```json
{
    "error": "Inmobiliaria no vinculada con MercadoLibre"
}
```
- **Salida de Error (503):**
```json
{
    "error": "MercadoLibre no está operativo en este momento"
}
```

#### Eliminación de Publicación

- **Ruta**: /<publicacion_id>
- **Método**: DELETE
- **Descripción**: Elimina una publicación en MercadoLibre y en la base de datos.
- **Salida Exitosa (200):**
```json
{
    "message": "Publicacion eliminada en MercadoLibre y en la base de datos"
}
```
- **Salida de Error (404):**
```json
{
    "error": "Publicación no encontrada"
}
```
- **Salida de Error (400):**
```json
{
    "error": "Inmobiliaria no vinculada con MercadoLibre"
}
```
- **Salida de Error (503):**
```json
{
    "error": "MercadoLibre no está operativo en este momento"
}
```

#### Obtener Publicaciones de Inmobiliaria

- **Ruta**: /inmobiliaria/<inmobiliary_id>
- **Método**: GET
- **Descripción**: Obtiene todas las publicaciones asociadas a una inmobiliaria.
- **Salida Exitosa (200):**
```json
[
    {
        "id": "MLU987654321",
        "inmobiliaria": "<inmobiliary_id>",
        "usuario": "<user_id>",
        "title": "Casa en venta",
        "price": 95000,
        "currency_id": "USD",
        "available_quantity": 2,
        ...
    },
    {
        "id": "MLU987654322",
        "inmobiliaria": "<inmobiliary_id>",
        "usuario": "<user_id>",
        "title": "Apartamento en alquiler",
        "price": 500,
        "currency_id": "USD",
        "available_quantity": 1,
        ...
    }
]
```

#### Obtener Publicaciones de Usuario

- **Ruta**: /usuario/<user_id>
- **Método**: GET
- **Descripción**: Obtiene todas las publicaciones asociadas a un usuario específico.
- **Salida Exitosa (200):**
```json
[
    {
        "id": "MLU987654321",
        "inmobiliaria": "<inmobiliary_id>",
        "usuario": "<user_id>",
        "title": "Casa en venta",
        "price": 95000,
        "currency_id": "USD",
        "available_quantity": 2,
        ...
    },
    {
        "id": "MLU987654322",
        "inmobiliaria": "<inmobiliary_id>",
        "usuario": "<user_id>",
        "title": "Apartamento en alquiler",
        "price": 500,
        "currency_id": "USD",
        "available_quantity": 1,
        ...
    }
]
```

## Versiones Disponibles

- **latest:** Última versión estable del servicio. Se recomienda su uso para entornos de producción.
- **v1.0:** Versión inicial del servicio.

Para cambiar la versión del servicio, modifica la etiqueta de imagen del contenedor en el archivo `deploy.yml` antes de ejecutar el flujo de trabajo.

## Contribución

Si deseas contribuir a este proyecto, sigue estos pasos:

1. Haz un fork del repositorio.
2. Crea una nueva rama para tu contribución (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza tus cambios y haz commits (`git commit -am 'Agrega nueva funcionalidad'`).
4. Sube tus cambios a tu repositorio remoto (`git push origin feature/nueva-funcionalidad`).
5. Crea un nuevo pull request en GitHub.

¡Esperamos tus contribuciones!
