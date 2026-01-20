import unittest
from Controladores.Modelos import Tablero, User
from Controladores.Listas import ListasController

class TestListasController(unittest.TestCase):
    def setUp(self):
        self.user = User(username="testuser", email="test@example.com")
        self.tablero = Tablero(name="Test Board", owner=self.user)
        self.controller = ListasController(self.tablero)

    def test_crear_lista(self):
        new_list = self.controller.crear_lista("To Do")
        self.assertEqual(new_list.name, "To Do")
        self.assertEqual(len(self.tablero.lists), 1)
        self.assertEqual(self.tablero.lists[0], new_list)

    def test_agregar_tarjeta(self):
        new_list = self.controller.crear_lista("To Do")
        card = self.controller.agregar_tarjeta(new_list.id, "Buy Milk", "Skimmed")
        self.assertIsNotNone(card)
        self.assertEqual(card.title, "Buy Milk")
        self.assertEqual(len(new_list.cards), 1)

    def test_eliminar_tarjeta(self):
        new_list = self.controller.crear_lista("To Do")
        card = self.controller.agregar_tarjeta(new_list.id, "Buy Milk")
        result = self.controller.eliminar_tarjeta(new_list.id, card.id)
        self.assertTrue(result)
        self.assertEqual(len(new_list.cards), 0)

    def test_mover_tarjeta(self):
        list1 = self.controller.crear_lista("List 1")
        list2 = self.controller.crear_lista("List 2")
        card = self.controller.agregar_tarjeta(list1.id, "Move Me")
        
        result = self.controller.mover_tarjeta(list1.id, list2.id, card.id)
        self.assertTrue(result)
        self.assertEqual(len(list1.cards), 0)
        self.assertEqual(len(list2.cards), 1)
        self.assertEqual(list2.cards[0].title, "Move Me")

    def test_renombrar_lista(self):
        new_list = self.controller.crear_lista("Old Name")
        result = self.controller.renombrar_lista(new_list.id, "New Name")
        self.assertTrue(result)
        self.assertEqual(new_list.name, "New Name")

    def test_eliminar_lista(self):
        new_list = self.controller.crear_lista("To Delete")
        result = self.controller.eliminar_lista(new_list.id)
        self.assertTrue(result)
        self.assertEqual(len(self.tablero.lists), 0)

if __name__ == '__main__':
    unittest.main()
