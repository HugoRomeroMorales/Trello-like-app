from typing import List, Optional
from Controladores.Modelos import Tablero, TrelloLista, Tarjeta, User
from Controladores.Controller_BD import SupabaseController

class ListasController:
    def __init__(self, tablero: Tablero, db_controller: SupabaseController):
        self.tablero = tablero
        self.db = db_controller

    def crear_lista(self, name: str) -> Optional[TrelloLista]:
        """Crea una lista y la añade al tablero."""
        # Calcula nueva posición
        current_max_pos = max([l.posicion for l in self.tablero.lists], default=-1)
        new_pos = current_max_pos + 1
        
        new_list = self.db.crear_lista(self.tablero.id, name, new_pos)
        if new_list:
            self.tablero.add_list(new_list)
            return new_list
        return None

    def eliminar_lista(self, list_id: str) -> bool:
        """Elimina una lista por ID."""
        if self.db.eliminar_lista(list_id):
            self.tablero.remove_list(list_id)
            return True
        return False

    def renombrar_lista(self, list_id: str, new_name: str) -> bool:
        """Renombra una lista."""
        if self.db.actualizar_lista(list_id, titulo=new_name):
            trello_list = self._obtener_lista_por_id(list_id)
            if trello_list:
                trello_list.titulo = new_name
                return True
        return False

    def agregar_tarjeta(self, list_id: str, title: str, description: str = "", user: Optional[User] = None) -> Optional[Tarjeta]:
        """Añade tarjeta a una lista."""
        trello_list = self._obtener_lista_por_id(list_id)
        if trello_list:
            current_max_pos = max([c.posicion for c in trello_list.cards], default=-1)
            new_pos = current_max_pos + 1
            
            new_card = self.db.crear_tarjeta(list_id, title, description, new_pos)
            if new_card:
                trello_list.add_card(new_card)
                return new_card
        return None

    def eliminar_tarjeta(self, list_id: str, card_id: str) -> bool:
        """Elimina tarjeta de una lista."""
        if self.db.eliminar_tarjeta(card_id):
            trello_list = self._obtener_lista_por_id(list_id)
            if trello_list:
                trello_list.remove_card(card_id)
                return True
        return False

    def renombrar_tarjeta(self, list_id: str, card_id: str, new_title: str) -> bool:
        """Renombra una tarjeta."""
        if self.db.actualizar_tarjeta(card_id, titulo=new_title):
            trello_list = self._obtener_lista_por_id(list_id)
            if trello_list:
                card = next((c for c in trello_list.cards if c.id == card_id), None)
                if card:
                    card.titulo = new_title
                    return True
        return False

    def mover_tarjeta(self, source_list_id: str, dest_list_id: str, card_id: str) -> bool:
        """Mueve tarjeta entre listas."""
        source_list = self._obtener_lista_por_id(source_list_id)
        dest_list = self._obtener_lista_por_id(dest_list_id)

        if source_list and dest_list:
            card_to_move = next((c for c in source_list.cards if c.id == card_id), None)
            if card_to_move:
                # Calcula nueva posición
                new_pos = max([c.posicion for c in dest_list.cards], default=-1) + 1
                
                if self.db.actualizar_posicion_tarjeta(card_id, dest_list_id, new_pos):
                    # Actualiza estado local
                    source_list.remove_card(card_id)
                    card_to_move.lista_id = dest_list_id
                    card_to_move.posicion = new_pos
                    dest_list.add_card(card_to_move)
                    return True
        return False

    def obtener_listas(self) -> List[TrelloLista]:
        """Devuelve listas del tablero."""
        # Refresca desde BD
        self.tablero.lists = self.db.obtener_listas(self.tablero.id)
        return self.tablero.lists

    def _obtener_lista_por_id(self, list_id: str) -> Optional[TrelloLista]:
        """Busca lista por ID."""
        return next((l for l in self.tablero.lists if l.id == list_id), None)


