from typing import List, Optional
from Controladores.Modelos import Tablero, TrelloLista, Tarjeta, User

class ListasController:
    def __init__(self, tablero: Tablero):
        self.tablero = tablero

    def crear_lista(self, name: str) -> TrelloLista:
        """Creates a new list and adds it to the board."""
        new_list = TrelloLista(name=name)
        self.tablero.add_list(new_list)
        return new_list

    def eliminar_lista(self, list_id: str) -> bool:
        """Deletes a list by its ID."""
        original_count = len(self.tablero.lists)
        self.tablero.lists = [l for l in self.tablero.lists if l.id != list_id]
        return len(self.tablero.lists) < original_count

    def renombrar_lista(self, list_id: str, new_name: str) -> bool:
        """Renames a list."""
        trello_list = self._obtener_lista_por_id(list_id)
        if trello_list:
            trello_list.name = new_name
            return True
        return False

    def agregar_tarjeta(self, list_id: str, title: str, description: str = "", user: Optional[User] = None) -> Optional[Tarjeta]:
        """Adds a card to a specific list."""
        trello_list = self._obtener_lista_por_id(list_id)
        if trello_list:
            new_card = Tarjeta(title=title, description=description)
            if user:
                new_card.assignees.append(user)
            trello_list.add_card(new_card)
            return new_card
        return None

    def eliminar_tarjeta(self, list_id: str, card_id: str) -> bool:
        """Removes a card from a list."""
        trello_list = self._obtener_lista_por_id(list_id)
        if trello_list:
            original_count = len(trello_list.cards)
            trello_list.remove_card(card_id)
            return len(trello_list.cards) < original_count
        return False

    def mover_tarjeta(self, source_list_id: str, dest_list_id: str, card_id: str) -> bool:
        """Moves a card from one list to another."""
        source_list = self._obtener_lista_por_id(source_list_id)
        dest_list = self._obtener_lista_por_id(dest_list_id)

        if source_list and dest_list:
            card_to_move = next((c for c in source_list.cards if c.id == card_id), None)
            if card_to_move:
                source_list.remove_card(card_id)
                dest_list.add_card(card_to_move)
                return True
        return False

    def obtener_listas(self) -> List[TrelloLista]:
        """Returns all lists in the board."""
        return self.tablero.lists

    def _obtener_lista_por_id(self, list_id: str) -> Optional[TrelloLista]:
        """Helper to find a list by ID."""
        return next((l for l in self.tablero.lists if l.id == list_id), None)
