from typing import List, Optional
from Controladores.Modelos import Tablero, TrelloLista, Tarjeta, User
from Controladores.Controller_BD import SupabaseController

class ListasController:
    def __init__(self, tablero: Tablero, db_controller: SupabaseController):
        self.tablero = tablero
        self.db = db_controller

    def crear_lista(self, name: str) -> Optional[TrelloLista]:
        current_max_pos = max([l.posicion for l in self.tablero.lists], default=-1)
        new_list = self.db.crear_lista(self.tablero.id, name, current_max_pos + 1)
        if new_list:
            self.tablero.add_list(new_list)
            return new_list
        return None

    def eliminar_lista(self, list_id: str) -> bool:
        if self.db.eliminar_lista(list_id):
            self.tablero.remove_list(list_id)
            return True
        return False

    def renombrar_lista(self, list_id: str, new_name: str) -> bool:
        if self.db.actualizar_lista(list_id, titulo=new_name):
            l = self._obtener_lista_por_id(list_id)
            if l:
                l.titulo = new_name
                return True
        return False

    def agregar_tarjeta(self, list_id: str, title: str, description: str = "", user: Optional[User] = None) -> Optional[Tarjeta]:
        l = self._obtener_lista_por_id(list_id)
        if l:
            pos = max([c.posicion for c in l.cards], default=-1) + 1
            new_card = self.db.crear_tarjeta(list_id, title, description, pos)
            if new_card:
                l.add_card(new_card)
                return new_card
        return None

    def eliminar_tarjeta(self, list_id: str, card_id: str) -> bool:
        if self.db.eliminar_tarjeta(card_id):
            l = self._obtener_lista_por_id(list_id)
            if l:
                l.remove_card(card_id)
                return True
        return False

    def renombrar_tarjeta(self, list_id: str, card_id: str, new_title: str) -> bool:
        if self.db.actualizar_tarjeta(card_id, titulo=new_title):
            l = self._obtener_lista_por_id(list_id)
            if l:
                c = next((x for x in l.cards if x.id == card_id), None)
                if c:
                    c.titulo = new_title
                    return True
        return False

    def actualizar_contenido_tarjeta(self, list_id: str, card_id: str, new_title: str, new_description: str) -> bool:
        """Actualiza título y descripción."""
        if self.db.actualizar_tarjeta(card_id, titulo=new_title, descripcion=new_description):
            l = self._obtener_lista_por_id(list_id)
            if l:
                c = next((x for x in l.cards if x.id == card_id), None)
                if c:
                    c.titulo = new_title
                    c.descripcion = new_description
                    return True
        return False

    def mover_tarjeta(self, source_list_id: str, dest_list_id: str, card_id: str) -> bool:
        s_list = self._obtener_lista_por_id(source_list_id)
        d_list = self._obtener_lista_por_id(dest_list_id)
        if s_list and d_list:
            card = next((c for c in s_list.cards if c.id == card_id), None)
            if card:
                new_pos = max([c.posicion for c in d_list.cards], default=-1) + 1
                if self.db.actualizar_posicion_tarjeta(card_id, dest_list_id, new_pos):
                    s_list.remove_card(card_id)
                    card.lista_id = dest_list_id
                    card.posicion = new_pos
                    d_list.add_card(card)
                    return True
        return False

    def obtener_listas(self) -> List[TrelloLista]:
        self.tablero.lists = self.db.obtener_listas(self.tablero.id)
        return self.tablero.lists

    def _obtener_lista_por_id(self, list_id: str) -> Optional[TrelloLista]:
        return next((l for l in self.tablero.lists if l.id == list_id), None)

    # --- NUEVOS MÉTODOS PARA ASIGNACIÓN ---
    def obtener_todos_usuarios(self) -> List[User]:
        return self.db.obtener_todos_usuarios()

    def gestionar_asignacion(self, list_id: str, card_id: str, user_id: str, asignar: bool) -> bool:
        exito = self.db.asignar_usuario_tarjeta(card_id, user_id) if asignar else self.db.desasignar_usuario_tarjeta(card_id, user_id)
        if exito:
            l = self._obtener_lista_por_id(list_id)
            if l:
                c = next((x for x in l.cards if x.id == card_id), None)
                if c: c.assignees = self.db.obtener_asignados_tarjeta(card_id)
            return True
        return False

    def cargar_asignados_iniciales(self):
        for lista in self.tablero.lists:
            for card in lista.cards:
                card.assignees = self.db.obtener_asignados_tarjeta(card.id)
                
    # ... (al final de Listas.py)

    # ===== MÉTODOS DE PAPELERA (TARJETAS) =====
    def obtener_papelera(self) -> List[Tarjeta]:
        return self.db.obtener_papelera(self.tablero.id)

    def restaurar_tarjeta(self, card_id: str) -> bool:
        return self.db.restaurar_tarjeta(card_id)

    def eliminar_definitivamente(self, card_id: str) -> bool:
        return self.db.eliminar_tarjeta_definitivamente(card_id)
    
    # ===== MÉTODOS DE PAPELERA (LISTAS/COLUMNAS) =====
    def obtener_papelera_listas(self) -> List[TrelloLista]:
        """Obtiene todas las listas eliminadas del tablero actual."""
        return self.db.obtener_papelera_listas(self.tablero.id)

    def restaurar_lista_papelera(self, list_id: str) -> bool:
        """Restaura una lista eliminada."""
        if self.db.restaurar_lista(list_id):
            # Recargar listas para actualizar la vista
            self.tablero.lists = self.db.obtener_listas(self.tablero.id)
            return True
        return False

    def eliminar_lista_definitivamente(self, list_id: str) -> bool:
        """Elimina permanentemente una lista de la base de datos."""
        return self.db.eliminar_lista_definitivamente(list_id)