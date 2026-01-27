import os
from typing import List, Optional
from datetime import datetime
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

from Controladores.Modelos import Tablero, TrelloLista, Tarjeta, User

class SupabaseController:
    def __init__(self, url: str = None, key: str = None):
        self.url = url or os.environ.get("SUPABASE_URL")
        self.key = key or os.environ.get("SUPABASE_KEY")
        self.client: Optional[Client] = None
        
        if self.url and self.key and create_client:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                print(f"Error conectando a Supabase: {e}")

    def obtener_usuario(self, user_id: str) -> Optional[User]:
        if not self.client: return None
        try:
            response = self.client.table('usuarios').select("*").eq('id', user_id).execute()
            if response.data:
                data = response.data[0]
                return User(username=data['username'], id=data['id'], created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')))
        except Exception as e:
            print(f"Error obteniendo usuario: {e}")
        return None

    def crear_usuario(self, user_id: str, username: str) -> Optional[User]:
        if not self.client: return None
        try:
            data = {"id": user_id, "username": username}
            response = self.client.table('usuarios').insert(data).execute()
            if response.data:
                return User(username=username, id=user_id)
        except Exception as e:
            print(f"Error creando usuario: {e}")
        return None

    def obtener_tableros(self) -> List[Tablero]:
        if not self.client: return []
        try:
            response = self.client.table('tableros').select("*").order('created_at').execute()
            boards = []
            for data in response.data:
                board = Tablero(
                    titulo=data['titulo'],
                    es_publico=data['es_publico'],
                    id=data['id'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                )
                board.lists = self.obtener_listas(board.id)
                boards.append(board)
            return boards
        except Exception as e:
            print(f"Error obteniendo tableros: {e}")
            return []

    def crear_tablero(self, titulo: str, es_publico: bool = False) -> Optional[Tablero]:
        if not self.client: return None
        try:
            data = {"titulo": titulo, "es_publico": es_publico}
            response = self.client.table('tableros').insert(data).execute()
            if response.data:
                d = response.data[0]
                return Tablero(
                    titulo=d['titulo'],
                    es_publico=d['es_publico'],
                    id=d['id'],
                    created_at=datetime.fromisoformat(d['created_at'].replace('Z', '+00:00'))
                )
        except Exception as e:
            print(f"Error creando tablero: {e}")
        return None

    def obtener_listas(self, board_id: str) -> List[TrelloLista]:
        if not self.client: return []
        try:
            response = self.client.table('listas').select("*").eq('tablero_id', board_id).order('posicion').execute()
            lists = []
            for data in response.data:
                t_list = TrelloLista(
                    titulo=data['titulo'],
                    tablero_id=data['tablero_id'],
                    posicion=data['posicion'],
                    id=data['id'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                )
                t_list.cards = self.obtener_tarjetas(t_list.id)
                lists.append(t_list)
            return lists
        except Exception as e:
            print(f"Error obteniendo listas: {e}")
            return []

    def crear_lista(self, board_id: str, titulo: str, posicion: int) -> Optional[TrelloLista]:
        if not self.client: return None
        try:
            data = {"tablero_id": board_id, "titulo": titulo, "posicion": posicion}
            response = self.client.table('listas').insert(data).execute()
            if response.data:
                d = response.data[0]
                return TrelloLista(
                    titulo=d['titulo'],
                    tablero_id=d['tablero_id'],
                    posicion=d['posicion'],
                    id=d['id'],
                    created_at=datetime.fromisoformat(d['created_at'].replace('Z', '+00:00'))
                )
        except Exception as e:
            print(f"Error creando lista: {e}")
        return None

    def obtener_tarjetas(self, list_id: str) -> List[Tarjeta]:
        if not self.client: return []
        try:
            response = self.client.table('tarjetas').select("*").eq('lista_id', list_id).order('posicion').execute()
            cards = []
            for data in response.data:
                card = Tarjeta(
                    titulo=data['titulo'],
                    lista_id=data['lista_id'],
                    descripcion=data.get('descripcion', ""),
                    posicion=data['posicion'],
                    id=data['id'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                )
                cards.append(card)
            return cards
        except Exception as e:
            print(f"Error obteniendo tarjetas: {e}")
            return []

    def crear_tarjeta(self, list_id: str, titulo: str, descripcion: str, posicion: int) -> Optional[Tarjeta]:
        if not self.client: return None
        try:
            data = {"lista_id": list_id, "titulo": titulo, "descripcion": descripcion, "posicion": posicion}
            response = self.client.table('tarjetas').insert(data).execute()
            if response.data:
                d = response.data[0]
                return Tarjeta(
                    titulo=d['titulo'],
                    lista_id=d['lista_id'],
                    descripcion=d.get('descripcion', ""),
                    posicion=d['posicion'],
                    id=d['id'],
                    created_at=datetime.fromisoformat(d['created_at'].replace('Z', '+00:00'))
                )
        except Exception as e:
            print(f"Error creando tarjeta: {e}")
        return None

    def actualizar_posicion_tarjeta(self, card_id: str, new_list_id: str, new_position: int) -> bool:
        if not self.client: return False
        try:
            data = {"lista_id": new_list_id, "posicion": new_position}
            self.client.table('tarjetas').update(data).eq('id', card_id).execute()
            return True
        except Exception as e:
            print(f"Error moviendo tarjeta: {e}")
            return False

    def eliminar_lista(self, list_id: str) -> bool:
        if not self.client: return False
        try:
            # Note: Cascade delete should handle cards if configured in DB, otherwise we might need to delete cards first.
            # Assuming Supabase/Postgres FKs are set to CASCADE.
            self.client.table('listas').delete().eq('id', list_id).execute()
            return True
        except Exception as e:
            print(f"Error eliminando lista: {e}")
            return False

    def actualizar_lista(self, list_id: str, titulo: str = None) -> bool:
        if not self.client: return False
        try:
            data = {}
            if titulo: data['titulo'] = titulo
            if not data: return False
            
            self.client.table('listas').update(data).eq('id', list_id).execute()
            return True
        except Exception as e:
            print(f"Error actualizando lista: {e}")
            return False

    def eliminar_tarjeta(self, card_id: str) -> bool:
        if not self.client: return False
        try:
            self.client.table('tarjetas').delete().eq('id', card_id).execute()
            return True
        except Exception as e:
            print(f"Error eliminando tarjeta: {e}")
            return False

    def actualizar_tarjeta(self, card_id: str, titulo: str = None, descripcion: str = None) -> bool:
        if not self.client: return False
        try:
            data = {}
            if titulo: data['titulo'] = titulo
            if descripcion is not None: data['descripcion'] = descripcion
            
            if not data: return False
            
            self.client.table('tarjetas').update(data).eq('id', card_id).execute()
            return True
        except Exception as e:
            print(f"Error actualizando tarjeta: {e}")
            return False

