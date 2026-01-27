import os
from typing import List, Optional
from datetime import datetime
import re
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

from Controladores.Modelos import Tablero, TrelloLista, Tarjeta, User

try:
    from Controladores.KEYBD import Config
    SUPABASE_URL_DEFAULT = Config.URL
    SUPABASE_KEY_DEFAULT = Config.KEY
except ImportError:
    SUPABASE_URL_DEFAULT = None
    SUPABASE_KEY_DEFAULT = None

def parse_supabase_datetime(date_string: str) -> datetime:
    """Parsea fechas de Supabase."""
    if not date_string:
        return datetime.now()
    try:
        date_string = date_string.replace('Z', '+00:00')
        pattern = r'(\.\d+)([+-]\d{2}:\d{2})'
        match = re.search(pattern, date_string)
        if match:
            microseconds = match.group(1)
            timezone = match.group(2)
            micros_digits = microseconds[1:]
            if len(micros_digits) < 6:
                micros_digits = micros_digits.ljust(6, '0')
            elif len(micros_digits) > 6:
                micros_digits = micros_digits[:6]
            base_date = date_string[:match.start()]
            date_string = f"{base_date}.{micros_digits}{timezone}"
        return datetime.fromisoformat(date_string)
    except Exception as e:
        print(f"Warning: Error parseando fecha '{date_string}': {e}")
        return datetime.now()

class SupabaseController:
    def __init__(self, url: str = None, key: str = None):
        self.url = url or SUPABASE_URL_DEFAULT or os.environ.get("SUPABASE_URL")
        self.key = key or SUPABASE_KEY_DEFAULT or os.environ.get("SUPABASE_KEY")
        self.client: Optional[Client] = None
        self.current_user = None  
        
        if self.url and self.key and create_client:
            try:
                self.client = create_client(self.url, self.key)
            except Exception as e:
                print(f"Error conectando a Supabase: {e}")

    # ===== MÉTODOS DE AUTENTICACIÓN =====
    def registrar_usuario(self, email: str, password: str, username: str = None) -> dict:
        if not self.client: return {"success": False, "error": "Cliente no disponible"}
        try:
            response = self.client.auth.sign_up({
                "email": email, "password": password,
                "options": {"data": {"username": username or email.split('@')[0]}}
            })
            if response.user:
                user_data = {"id": response.user.id, "username": username or email.split('@')[0]}
                try:
                    self.client.table('usuarios').insert(user_data).execute()
                except Exception: pass
                self.current_user = response.user
                return {"success": True, "user": response.user, "session": response.session}
            return {"success": False, "error": "No se pudo crear el usuario"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def iniciar_sesion(self, email: str, password: str) -> dict:
        if not self.client: return {"success": False, "error": "Cliente no disponible"}
        try:
            response = self.client.auth.sign_in_with_password({"email": email, "password": password})
            if response.user:
                self.current_user = response.user
                return {"success": True, "user": response.user, "session": response.session}
            return {"success": False, "error": "Credenciales inválidas"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cerrar_sesion(self) -> bool:
        if not self.client: return False
        try:
            self.client.auth.sign_out()
            self.current_user = None
            return True
        except Exception: return False
    
    def obtener_sesion_actual(self) -> Optional[dict]:
        if not self.client: return None
        try:
            session = self.client.auth.get_session()
            if session:
                self.current_user = self.client.auth.get_user()
                return {"user": self.current_user, "session": session}
            return None
        except Exception: return None
    
    def obtener_usuario_actual(self) -> Optional[User]:
        if not self.client or not self.current_user: return None
        try:
            user_id = self.current_user.id
            response = self.client.table('usuarios').select("*").eq('id', user_id).execute()
            if response.data:
                data = response.data[0]
                return User(username=data.get('username', self.current_user.email), id=data['id'], created_at=parse_supabase_datetime(data['created_at']))
            else:
                username = self.current_user.user_metadata.get('username', self.current_user.email)
                return User(username=username, id=self.current_user.id)
        except Exception:
            return User(username=getattr(self.current_user, 'email', 'Usuario'), id=self.current_user.id) if self.current_user else None

    # ===== GESTIÓN DE TABLEROS Y LISTAS =====
    def obtener_tableros(self) -> List[Tablero]:
            if not self.client: return []
            try:
                # CAMBIO: Filtrar por eliminada = False
                response = self.client.table('tableros').select("*").eq('eliminada', False).order('created_at').execute()
                boards = []
                for data in response.data:
                    board = Tablero(
                        titulo=data['titulo'],
                        es_publico=data['es_publico'],
                        id=data['id'],
                        created_at=parse_supabase_datetime(data['created_at'])
                    )
                    # No cargamos listas aquí para ir más rápido en la vista general
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
                return Tablero(titulo=d['titulo'], es_publico=d['es_publico'], id=d['id'], created_at=parse_supabase_datetime(d['created_at']))
        except Exception: return None

    def eliminar_tablero(self, board_id: str) -> bool:
        if not self.client: return False
        try:
            # CAMBIO: Update en lugar de Delete
            self.client.table('tableros').update({'eliminada': True}).eq('id', board_id).execute()
            return True
        except Exception as e:
            print(f"Error enviando tablero a papelera: {e}")
            return False

    def obtener_listas(self, board_id: str) -> List[TrelloLista]:
        if not self.client: return []
        try:
            # Filtrar solo las listas no eliminadas
            response = self.client.table('listas').select("*").eq('tablero_id', board_id).eq('eliminada', False).order('posicion').execute()
            lists = []
            for data in response.data:
                t_list = TrelloLista(titulo=data['titulo'], tablero_id=data['tablero_id'], posicion=data['posicion'], id=data['id'], created_at=parse_supabase_datetime(data['created_at']))
                t_list.cards = self.obtener_tarjetas(t_list.id)
                lists.append(t_list)
            return lists
        except Exception: return []

    def crear_lista(self, board_id: str, titulo: str, posicion: int) -> Optional[TrelloLista]:
        if not self.client: return None
        try:
            data = {"tablero_id": board_id, "titulo": titulo, "posicion": posicion}
            response = self.client.table('listas').insert(data).execute()
            if response.data:
                d = response.data[0]
                return TrelloLista(titulo=d['titulo'], tablero_id=d['tablero_id'], posicion=d['posicion'], id=d['id'], created_at=parse_supabase_datetime(d['created_at']))
        except Exception: return None

    def eliminar_lista(self, list_id: str) -> bool:
        """Soft delete - Envía la lista a la papelera."""
        if not self.client: return False
        try:
            self.client.table('listas').update({'eliminada': True}).eq('id', list_id).execute()
            return True
        except Exception as e:
            print(f"Error enviando lista a papelera: {e}")
            return False

    def actualizar_lista(self, list_id: str, titulo: str = None) -> bool:
        if not self.client: return False
        try:
            if titulo:
                self.client.table('listas').update({'titulo': titulo}).eq('id', list_id).execute()
                return True
        except Exception: return False

    # ===== GESTIÓN DE TARJETAS =====
    def obtener_tarjetas(self, list_id: str) -> List[Tarjeta]:
            if not self.client: return []
            try:
                # CAMBIO: Añadido .eq('eliminada', False)
                response = self.client.table('tarjetas').select("*").eq('lista_id', list_id).eq('eliminada', False).order('posicion').execute()
                cards = []
                for data in response.data:
                    cards.append(Tarjeta(
                        titulo=data['titulo'],
                        lista_id=data['lista_id'],
                        descripcion=data.get('descripcion', ""),
                        posicion=data['posicion'],
                        id=data['id'],
                        created_at=parse_supabase_datetime(data['created_at'])
                    ))
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
                    titulo=d['titulo'], lista_id=d['lista_id'], descripcion=d.get('descripcion', ""),
                    posicion=d['posicion'], id=d['id'], created_at=parse_supabase_datetime(d['created_at'])
                )
        except Exception: return None

    def eliminar_tarjeta(self, card_id: str) -> bool:
            if not self.client: return False
            try:
                # CAMBIO: Update en lugar de Delete
                self.client.table('tarjetas').update({'eliminada': True}).eq('id', card_id).execute()
                return True
            except Exception as e:
                print(f"Error enviando a papelera: {e}")
                return False

    def actualizar_tarjeta(self, card_id: str, titulo: str = None, descripcion: str = None) -> bool:
        if not self.client: return False
        try:
            data = {}
            if titulo: data['titulo'] = titulo
            if descripcion is not None: data['descripcion'] = descripcion
            if data:
                self.client.table('tarjetas').update(data).eq('id', card_id).execute()
                return True
        except Exception: return False

    def actualizar_posicion_tarjeta(self, card_id: str, new_list_id: str, new_position: int) -> bool:
        if not self.client: return False
        try:
            self.client.table('tarjetas').update({"lista_id": new_list_id, "posicion": new_position}).eq('id', card_id).execute()
            return True
        except Exception: return False

    # ===== GESTIÓN DE ASIGNACIONES (NUEVO) =====
    def obtener_todos_usuarios(self) -> List[User]:
        if not self.client: return []
        try:
            response = self.client.table('usuarios').select("*").execute()
            return [User(username=d['username'], id=d['id']) for d in response.data]
        except Exception as e:
            print(f"Error obteniendo usuarios: {e}")
            return []

    def asignar_usuario_tarjeta(self, card_id: str, user_id: str) -> bool:
        if not self.client: return False
        try:
            self.client.table('tarjeta_usuarios').insert({"tarjeta_id": card_id, "usuario_id": user_id}).execute()
            return True
        except Exception as e:
            if "unique" not in str(e).lower(): print(f"Error asignando: {e}")
            return False

    def desasignar_usuario_tarjeta(self, card_id: str, user_id: str) -> bool:
        if not self.client: return False
        try:
            self.client.table('tarjeta_usuarios').delete().match({"tarjeta_id": card_id, "usuario_id": user_id}).execute()
            return True
        except Exception as e:
            print(f"Error desasignando: {e}")
            return False

    def obtener_asignados_tarjeta(self, card_id: str) -> List[User]:
        if not self.client: return []
        try:
            response = self.client.table('tarjeta_usuarios').select("usuario_id, usuarios(username)").eq('tarjeta_id', card_id).execute()
            users = []
            for item in response.data:
                udata = item.get('usuarios')
                if udata: users.append(User(username=udata.get('username', '?'), id=item['usuario_id']))
            return users
        except Exception as e:
            print(f"Error obteniendo asignados: {e}")
            return []
        
        # ===== PAPELERA DE RECICLAJE =====
    def obtener_papelera(self, board_id: str) -> List[Tarjeta]:
        """Obtiene todas las tarjetas eliminadas de un tablero específico."""
        if not self.client: return []
        try:
            # Hacemos join con listas para filtrar por tablero_id
            response = self.client.table('tarjetas').select("*, listas!inner(tablero_id)").eq('listas.tablero_id', board_id).eq('eliminada', True).execute()
            cards = []
            for data in response.data:
                cards.append(Tarjeta(
                    titulo=data['titulo'],
                    lista_id=data['lista_id'],
                    descripcion=data.get('descripcion', ""),
                    posicion=data['posicion'],
                    id=data['id'],
                    created_at=parse_supabase_datetime(data['created_at'])
                ))
            return cards
        except Exception as e:
            print(f"Error obteniendo papelera: {e}")
            return []

    def restaurar_tarjeta(self, card_id: str) -> bool:
        """Devuelve una tarjeta al tablero."""
        if not self.client: return False
        try:
            self.client.table('tarjetas').update({'eliminada': False}).eq('id', card_id).execute()
            return True
        except Exception as e:
            print(f"Error restaurando tarjeta: {e}")
            return False

    def eliminar_tarjeta_definitivamente(self, card_id: str) -> bool:
        """Borra la tarjeta para siempre (Hard Delete)."""
        if not self.client: return False
        try:
            self.client.table('tarjetas').delete().eq('id', card_id).execute()
            return True
        except Exception as e:
            print(f"Error eliminando definitivamente: {e}")
            return False
        
    # ===== PAPELERA DE TABLEROS =====
    def obtener_papelera_tableros(self) -> List[Tablero]:
        """Obtiene tableros eliminados."""
        if not self.client: return []
        try:
            response = self.client.table('tableros').select("*").eq('eliminada', True).execute()
            return [Tablero(titulo=d['titulo'], id=d['id']) for d in response.data]
        except Exception as e:
            print(f"Error obteniendo papelera tableros: {e}")
            return []

    def restaurar_tablero(self, board_id: str) -> bool:
        if not self.client: return False
        try:
            self.client.table('tableros').update({'eliminada': False}).eq('id', board_id).execute()
            return True
        except Exception: return False

    def eliminar_tablero_definitivamente(self, board_id: str) -> bool:
        if not self.client: return False
        try:
            self.client.table('tableros').delete().eq('id', board_id).execute()
            return True
        except Exception: return False

    # ===== PAPELERA DE LISTAS/COLUMNAS =====
    def obtener_papelera_listas(self, board_id: str) -> List[TrelloLista]:
        """Obtiene todas las listas eliminadas de un tablero específico."""
        if not self.client: return []
        try:
            response = self.client.table('listas').select("*").eq('tablero_id', board_id).eq('eliminada', True).execute()
            lists = []
            for data in response.data:
                t_list = TrelloLista(
                    titulo=data['titulo'],
                    tablero_id=data['tablero_id'],
                    posicion=data['posicion'],
                    id=data['id'],
                    created_at=parse_supabase_datetime(data['created_at'])
                )
                lists.append(t_list)
            return lists
        except Exception as e:
            print(f"Error obteniendo papelera de listas: {e}")
            return []

    def restaurar_lista(self, list_id: str) -> bool:
        """Devuelve una lista al tablero."""
        if not self.client: return False
        try:
            self.client.table('listas').update({'eliminada': False}).eq('id', list_id).execute()
            return True
        except Exception as e:
            print(f"Error restaurando lista: {e}")
            return False

    def eliminar_lista_definitivamente(self, list_id: str) -> bool:
        """Borra la lista para siempre (Hard Delete)."""
        if not self.client: return False
        try:
            self.client.table('listas').delete().eq('id', list_id).execute()
            return True
        except Exception as e:
            print(f"Error eliminando lista definitivamente: {e}")
            return False