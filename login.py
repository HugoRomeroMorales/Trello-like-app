import sys
import os
from PyQt5 import QtWidgets, uic
from Controladores.Controller_BD import SupabaseController

# Ensure we can find the UI file
current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "Pantallas", "Login.ui")

class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        try:
            uic.loadUi(ui_path, self)
        except FileNotFoundError:
            print(f"Error: Could not find UI file at {ui_path}")
            sys.exit(1)
        
        # Inicializar controlador de BD
        self.db_controller = SupabaseController()
        
        # Cargar estilo de login
        self.cargar_estilo()
        
        # Conectar botones
        self.configurar_conexiones()
        
        # Referencia a la ventana principal
        self.main_window = None
        
        # Ocultar mensaje de error inicialmente
        if hasattr(self, 'Error'):
            self.Error.hide()
    
    def cargar_estilo(self):
        """Carga el estilo brutalista por defecto para el login"""
        style_path = os.path.join(current_dir, "estilos", "brutalista_salmon.qss")
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                style = f.read()
                self.setStyleSheet(style)
        except Exception as e:
            print(f"Error cargando estilo: {e}")
    
    def configurar_conexiones(self):
        """Conecta los botones con sus funciones"""
        # Botón de iniciar sesión
        if hasattr(self, 'Primary'):
            self.Primary.clicked.connect(self.iniciar_sesion)
        
        # Botón de invitado
        if hasattr(self, 'btnInvitado'):
            self.btnInvitado.clicked.connect(self.entrar_como_invitado)
        
        # Botón de crear cuenta
        if hasattr(self, 'Link'):
            self.Link.clicked.connect(self.crear_cuenta)
        
        # Presionar Enter en los campos de texto también inicia sesión
        if hasattr(self, 'txtUsuario'):
            self.txtUsuario.returnPressed.connect(self.iniciar_sesion)
        if hasattr(self, 'Contrasena'):
            self.Contrasena.returnPressed.connect(self.iniciar_sesion)
    
    def iniciar_sesion(self):
        """Valida las credenciales e inicia sesión con Supabase"""
        email = self.txtUsuario.text().strip()
        password = self.Contrasena.text().strip()
        
        # Validación básica
        if not email or not password:
            self.mostrar_error("Por favor, completa todos los campos")
            return
        
        # Deshabilitar botón mientras se procesa
        self.Primary.setEnabled(False)
        self.Primary.setText("Iniciando...")
        
        # Intentar iniciar sesión con Supabase
        resultado = self.db_controller.iniciar_sesion(email, password)
        
        if resultado["success"]:
            # Obtener información del usuario
            user = self.db_controller.obtener_usuario_actual()
            username = user.username if user else email.split('@')[0]
            
            # Abrir ventana principal
            self.abrir_ventana_principal(username)
        else:
            # Mostrar error
            error_msg = resultado.get("error", "Error desconocido")
            self.mostrar_error(error_msg)
            
            # Rehabilitar botón
            self.Primary.setEnabled(True)
            self.Primary.setText("Iniciar sesión")
    
    def entrar_como_invitado(self):
        """Entra como invitado sin necesidad de credenciales"""
        # Modo invitado - sin autenticación de Supabase
        # Solo abre la ventana principal con datos locales
        self.abrir_ventana_principal("Invitado", modo_invitado=True)
    
    def crear_cuenta(self):
        """Muestra diálogo para crear cuenta nueva"""
        # Crear diálogo personalizado
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Crear Cuenta")
        dialog.setMinimumWidth(350)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Campos del formulario
        layout.addWidget(QtWidgets.QLabel("Email:"))
        txt_email = QtWidgets.QLineEdit()
        txt_email.setPlaceholderText("tu@email.com")
        layout.addWidget(txt_email)
        
        layout.addWidget(QtWidgets.QLabel("Nombre de usuario:"))
        txt_username = QtWidgets.QLineEdit()
        txt_username.setPlaceholderText("Tu nombre")
        layout.addWidget(txt_username)
        
        layout.addWidget(QtWidgets.QLabel("Contraseña:"))
        txt_password = QtWidgets.QLineEdit()
        txt_password.setEchoMode(QtWidgets.QLineEdit.Password)
        txt_password.setPlaceholderText("Mínimo 6 caracteres")
        layout.addWidget(txt_password)
        
        layout.addWidget(QtWidgets.QLabel("Confirmar contraseña:"))
        txt_confirm = QtWidgets.QLineEdit()
        txt_confirm.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addWidget(txt_confirm)
        
        # Botones
        btn_layout = QtWidgets.QHBoxLayout()
        btn_crear = QtWidgets.QPushButton("Crear cuenta")
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_layout.addWidget(btn_crear)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        # Conectar botones
        btn_cancelar.clicked.connect(dialog.reject)
        
        def procesar_registro():
            email = txt_email.text().strip()
            username = txt_username.text().strip()
            password = txt_password.text()
            confirm = txt_confirm.text()
            
            # Validaciones
            if not email or not username or not password:
                QtWidgets.QMessageBox.warning(dialog, "Error", "Por favor, completa todos los campos")
                return
            
            if '@' not in email:
                QtWidgets.QMessageBox.warning(dialog, "Error", "Email inválido")
                return
            
            if len(password) < 6:
                QtWidgets.QMessageBox.warning(dialog, "Error", "La contraseña debe tener al menos 6 caracteres")
                return
            
            if password != confirm:
                QtWidgets.QMessageBox.warning(dialog, "Error", "Las contraseñas no coinciden")
                return
            
            # Intentar registrar
            btn_crear.setEnabled(False)
            btn_crear.setText("Creando...")
            
            resultado = self.db_controller.registrar_usuario(email, password, username)
            
            if resultado["success"]:
                QtWidgets.QMessageBox.information(
                    dialog, 
                    "Éxito", 
                    "Cuenta creada exitosamente.\n\nYa puedes iniciar sesión con tus credenciales."
                )
                dialog.accept()
            else:
                error_msg = resultado.get("error", "Error desconocido")
                QtWidgets.QMessageBox.warning(dialog, "Error", f"No se pudo crear la cuenta:\n{error_msg}")
                btn_crear.setEnabled(True)
                btn_crear.setText("Crear cuenta")
        
        btn_crear.clicked.connect(procesar_registro)
        
        # Mostrar diálogo
        dialog.exec_()
    
    def abrir_ventana_principal(self, username, modo_invitado=False):
        """Abre la ventana principal de la aplicación"""
        from main import MainWindow
        
        # Crear ventana principal
        self.main_window = MainWindow()
        
        # Si no es modo invitado, pasar el controlador de BD con sesión activa
        if not modo_invitado:
            self.main_window.db_controller = self.db_controller
        
        # Pasar el nombre de usuario
        if hasattr(self.main_window, 'current_user'):
            self.main_window.current_user.username = username
        
        # Actualizar label de usuario si existe
        if hasattr(self.main_window, 'lblUsuarioActual'):
            self.main_window.lblUsuarioActual.setText(f"Usuario: {username}")
        
        # Conectar señal de cierre de sesión
        if hasattr(self.main_window, 'sesion_cerrada'):
            self.main_window.sesion_cerrada.connect(self.volver_al_login)
        
        # Mostrar ventana principal y ocultar login
        self.main_window.show()
        self.hide()
    
    def volver_al_login(self):
        """Vuelve a mostrar la ventana de login"""
        # Cerrar sesión en Supabase si existe
        if self.db_controller:
            self.db_controller.cerrar_sesion()
        
        # Limpiar campos
        if hasattr(self, 'txtUsuario'):
            self.txtUsuario.clear()
        if hasattr(self, 'Contrasena'):
            self.Contrasena.clear()
        if hasattr(self, 'Error'):
            self.Error.hide()
        
        # Rehabilitar botón
        if hasattr(self, 'Primary'):
            self.Primary.setEnabled(True)
            self.Primary.setText("Iniciar sesión")
        
        # Mostrar ventana de login
        self.show()
        
        # Cerrar ventana principal si existe
        if self.main_window:
            self.main_window.close()
            self.main_window = None
    
    def mostrar_error(self, mensaje):
        """Muestra un mensaje de error"""
        if hasattr(self, 'Error'):
            self.Error.setText(mensaje)
            self.Error.show()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())

