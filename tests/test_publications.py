import unittest
from unittest.mock import patch, MagicMock
from app import app, inmobiliary_collection, publicaciones_collection, sincronizar_publicaciones

class PublicationsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('app.inmobiliary_collection.find_one')
    def test_chequear_vinculacion_inmobiliaria_no_encontrada(self, mock_find_one):
        mock_find_one.return_value = None
        response = self.app.get('/chequear_vinculacion/test_inmobiliary_id')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Inmobiliaria no encontrada', response.data)

    @patch('app.inmobiliary_collection.find_one')
    def test_chequear_vinculacion_inmobiliaria_no_vinculada(self, mock_find_one):
        mock_find_one.return_value = {"_id": "test_inmobiliary_id"}
        response = self.app.get('/chequear_vinculacion/test_inmobiliary_id')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Inmobiliaria no vinculada con MercadoLibre', response.data)

    @patch('app.inmobiliary_collection.find_one')
    def test_chequear_vinculacion_inmobiliaria_vinculada(self, mock_find_one):
        mock_find_one.return_value = {"_id": "test_inmobiliary_id", "mercadolibre_token": "test_token"}
        response = self.app.get('/chequear_vinculacion/test_inmobiliary_id')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Inmobiliaria vinculada con MercadoLibre', response.data)
    
    @patch('app.requests.get')
    @patch('app.publicaciones_collection.update_one')
    def test_sincronizar_publicaciones(self, mock_update_one, mock_get):
        # Simular la respuesta de la API de MercadoLibre para obtener publicaciones
        mock_get.return_value.json.return_value = {"results": ["123"]}
        mock_get.return_value.status_code = 200
        
        # Simular la respuesta de la API de MercadoLibre para obtener la publicación específica
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"results": ["123"]}),  # Primer llamado para buscar publicaciones
            MagicMock(status_code=200, json=lambda: {"id": "123", "title": "Test"})  # Segundo llamado para obtener publicación específica
        ]

        # Llamar a la función de sincronización
        try:
            sincronizar_publicaciones('test_inmobiliary_id', 'test_token')
        except Exception:
            self.fail("sincronizar_publicaciones() raised Exception unexpectedly!")

        # Verificar que se haya llamado update_one con los parámetros correctos
        mock_update_one.assert_called_with(
            {"_id": "123"},
            {"$set": {
                "inmobiliary_id": "test_inmobiliary_id",
                "user_id": None,  # Asociar a usuario nulo inicialmente
                "id": "123",
                "title": "Test"  # Asegúrate de incluir aquí todos los campos relevantes de la publicación
            }},
            upsert=True
        )

    @patch('app.requests.post')
    def test_crear_publicacion(self, mock_post):
        inmobiliaria = {"_id": "test_inmobiliary_id", "mercadolibre_token": "test_token"}
        with patch.object(inmobiliary_collection, 'find_one', return_value=inmobiliaria):
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {"id": "123"}
            response = self.app.post('/test_inmobiliary_id/test_user_id', json={})
            self.assertEqual(response.status_code, 201)
            self.assertIn(b'Publicacion creada y sincronizada con MercadoLibre', response.data)

    @patch('app.requests.put')
    def test_modificar_publicacion(self, mock_put):
        inmobiliaria = {"_id": "test_inmobiliary_id", "mercadolibre_token": "test_token"}
        publicacion = {"id": "123"}  # Simulamos la publicación que recibimos de MercadoLibre
        with patch.object(inmobiliary_collection, 'find_one', return_value=inmobiliaria):
            mock_put.return_value.status_code = 200
            mock_put.return_value.json.return_value = publicacion
            response = self.app.put('/123', json={})
            self.assertEqual(response.status_code, 200)

    @patch('app.requests.delete')
    def test_borrar_publicacion(self, mock_delete):
        inmobiliaria = {"_id": "test_inmobiliary_id", "mercadolibre_token": "test_token"}
        publicacion = {"_id": "123", "inmobiliary_id": "test_inmobiliary_id"}
        with patch.object(inmobiliary_collection, 'find_one', return_value=inmobiliaria):
            with patch.object(publicaciones_collection, 'find_one', return_value=publicacion):
                mock_delete.return_value.status_code = 200
                response = self.app.delete('/123')
                self.assertEqual(response.status_code, 200)

    @patch('app.publicaciones_collection.find')
    def test_obtener_publicaciones_inmobiliaria(self, mock_find):
        publicaciones = [
            {"_id": "123", "inmobiliary_id": "test_inmobiliary_id", "user_id": "test_user_id"},
            {"_id": "124", "inmobiliary_id": "test_inmobiliary_id", "user_id": "test_user_id"}
        ]
        mock_find.return_value = MagicMock()
        mock_find.return_value.__iter__.return_value = publicaciones

        response = self.app.get('/inmobiliaria/test_inmobiliary_id')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'123', response.data)
        self.assertIn(b'124', response.data)

    @patch('app.publicaciones_collection.find')
    def test_obtener_publicaciones_usuario(self, mock_find):
        publicaciones = [
            {"_id": "123", "inmobiliary_id": "test_inmobiliary_id", "user_id": "test_user_id"},
            {"_id": "124", "inmobiliary_id": "test_inmobiliary_id", "user_id": "test_user_id"}
        ]
        mock_find.return_value = MagicMock()
        mock_find.return_value.__iter__.return_value = publicaciones

        response = self.app.get('/usuario/test_user_id')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'123', response.data)
        self.assertIn(b'124', response.data)

if __name__ == '__main__':
    unittest.main()
