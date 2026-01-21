import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from Controladores.Controller_BD import SupabaseController
from Controladores.Modelos import Tablero, TrelloLista, Tarjeta

class TestSupabaseController(unittest.TestCase):
    def setUp(self):
        # Mock the supabase client
        self.mock_client = MagicMock()
        self.controller = SupabaseController("http://mock-url", "mock-key")
        self.controller.client = self.mock_client

    def test_obtener_tableros(self):
        # Setup mock response
        mock_data = [
            {
                "id": "board-1",
                "titulo": "Test Board",
                "es_publico": False,
                "created_at": "2023-01-01T12:00:00Z"
            }
        ]
        self.mock_client.table.return_value.select.return_value.order.return_value.execute.return_value.data = mock_data
        
        # Mock obtener_listas to return empty list
        with patch.object(self.controller, 'obtener_listas', return_value=[]):
            boards = self.controller.obtener_tableros()
            
            self.assertEqual(len(boards), 1)
            self.assertEqual(boards[0].titulo, "Test Board")
            self.assertEqual(boards[0].id, "board-1")

    def test_crear_tablero(self):
        mock_data = {
            "id": "board-new",
            "titulo": "New Board",
            "es_publico": True,
            "created_at": "2023-01-01T12:00:00Z"
        }
        self.mock_client.table.return_value.insert.return_value.execute.return_value.data = [mock_data]
        
        board = self.controller.crear_tablero("New Board", True)
        self.assertIsNotNone(board)
        self.assertEqual(board.titulo, "New Board")
        self.assertTrue(board.es_publico)

    def test_obtener_listas_y_tarjetas(self):
        # Mock lists
        mock_lists_data = [
            {
                "id": "list-1",
                "titulo": "To Do",
                "tablero_id": "board-1",
                "posicion": 0,
                "created_at": "2023-01-01T12:00:00Z"
            }
        ]
        
        # Mock cards
        mock_cards_data = [
            {
                "id": "card-1",
                "titulo": "Task 1",
                "lista_id": "list-1",
                "descripcion": "Desc",
                "posicion": 0,
                "created_at": "2023-01-01T12:00:00Z"
            }
        ]
        
        # We need to handle different table calls
        # This is a bit complex with chained mocks, so let's mock the methods instead for integration logic
        
        with patch.object(self.controller, 'obtener_tarjetas') as mock_obtener_tarjetas:
            mock_obtener_tarjetas.return_value = [Tarjeta(titulo="Task 1", lista_id="list-1")]
            
            self.mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = mock_lists_data
            
            lists = self.controller.obtener_listas("board-1")
            
            self.assertEqual(len(lists), 1)
            self.assertEqual(lists[0].titulo, "To Do")
            self.assertEqual(len(lists[0].cards), 1)
            self.assertEqual(lists[0].cards[0].titulo, "Task 1")

if __name__ == '__main__':
    unittest.main()

