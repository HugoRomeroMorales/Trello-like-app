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
    """
    Parsea fechas de Supabase que pueden tener formatos no estándar de microsegundos.
    """
    if not date_string:
        return datetime.now()
    
    try:
        # Reemplazar 'Z' con '+00:00'
        date_string = date_string.replace('Z', '+00:00')
        
        # Normalizar microsegundos a 6 dígitos
        pattern = r'(\.\d+)([+-]\d{2}:\d{2})'
        match = re.search(pattern, date_string)
        
        if match:
            microseconds = match.group(1)  # .1226
            timezone = match.group(2)      # +00:00
            micros_digits = microseconds[1:]  # quitar punto
            
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
        """Registra un nuevo usuario con email y contraseña"""
        if not self.client:
            return {"success": False, "error": "Cliente de Supabase no disponible"}
        
        try:
            # Registrar usuario en Supabase Auth
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "username": username or email.split('@')[0]
                    }
                }
            })
            
            if response.user:
                # Crear entrada en la tabla de usuarios
                user_data = {
                    "id": response.user.id,
                    "username": username or email.split('@')[0]
                }
                try:
                    self.client.table('usuarios').insert(user_data).execute()
                except Exception as e:
                    print(f"Advertencia: No se pudo crear entrada en tabla usuarios: {e}")
                
                self.current_user = response.user
                return {
                    "success": True,
                    "user": response.user,
                    "session": response.session
                }
            else:
                return {"success": False, "error": "No se pudo crear el usuario"}
                
        except Exception as e:
            error_msg = str(e)
            print(f"Error en registro: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def iniciar_sesion(self, email: str, password: str) -> dict:
        """Inicia sesión con email y contraseña"""
        if not self.client:
            return {"success": False, "error": "Cliente de Supabase no disponible"}
        
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user:
                self.current_user = response.user
                return {
                    "success": True,
                    "user": response.user,
                    "session": response.session
                }
            else:
                return {"success": False, "error": "Credenciales inválidas"}
                
        except Exception as e:
            error_msg = str(e)
            print(f"Error en login: {error_msg}")
            
            # Mensajes de error más amigables
            if "Invalid login credentials" in error_msg:
                return {"success": False, "error": "Email o contraseña incorrectos"}
            elif "Email not confirmed" in error_msg:
                return {"success": False, "error": "Por favor, confirma tu email primero"}
            else:
                return {"success": False, "error": error_msg}
    
    def cerrar_sesion(self) -> bool:
        """Cierra la sesión actual"""
        if not self.client:
            return False
        
        try:
            self.client.auth.sign_out()
            self.current_user = None
            return True
        except Exception as e:
            print(f"Error cerrando sesión: {e}")
            return False
    
    def obtener_sesion_actual(self) -> Optional[dict]:
        """Obtiene la sesión actual si existe"""
        if not self.client:
            return None
        
        try:
            session = self.client.auth.get_session()
            if session:
                self.current_user = self.client.auth.get_user()
                return {"user": self.current_user, "session": session}
            return None
        except Exception as e:
            print(f"Error obteniendo sesión: {e}")
            return None
    
    def obtener_usuario_actual(self) -> Optional[User]:
        """Obtiene el usuario actual autenticado"""
        if not self.client or not self.current_user:
            return None
        
        try:
            # Obtener metadata adicional de la tabla usuarios si existe
            user_id = self.current_user.id
            response = self.client.table('usuarios').select("*").eq('id', user_id).execute()
            
            if response.data:
                data = response.data[0]
                return User(
                    username=data.get('username', self.current_user.email),
                    id=data['id'],
                    created_at=parse_supabase_datetime(data['created_at'])
                )
            else:
                # Si no hay entrada en la tabla, usar datos del auth
                username = self.current_user.user_metadata.get('username', self.current_user.email)
                return User(username=username, id=self.current_user.id)
                
        except Exception as e:
            print(f"Error obteniendo usuario actual: {e}")
            # Fallback a datos básicos del auth
            if self.current_user:
                username = getattr(self.current_user, 'email', 'Usuario')
                return User(username=username, id=self.current_user.id)
            return None


    def obtener_usuario(self, user_id: str) -> Optional[User]:
        if not self.client: return None
        try:
            response = self.client.table('usuarios').select("*").eq('id', user_id).execute()
            if response.data:
                data = response.data[0]
                return User(username=data['username'], id=data['id'], created_at=parse_supabase_datetime(data['created_at']))
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
                    created_at=parse_supabase_datetime(data['created_at'])
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
                    created_at=parse_supabase_datetime(d['created_at'])
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
                    created_at=parse_supabase_datetime(data['created_at'])
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
                    created_at=parse_supabase_datetime(d['created_at'])
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
                    created_at=parse_supabase_datetime(data['created_at'])
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
                    created_at=parse_supabase_datetime(d['created_at'])
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

    def eliminar_tablero(self, board_id: str) -> bool:
        if not self.client: return False
        try:
            # Note: Cascade delete should handle lists and cards if configured in DB
            # Assuming Supabase/Postgres FKs are set to CASCADE
            self.client.table('tableros').delete().eq('id', board_id).execute()
            return True
        except Exception as e:
            print(f"Error eliminando tablero: {e}")
            return False

