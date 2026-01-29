import sys
import os
from PyQt5 import QtWidgets, uic, QtGui, QtCore
from PyQt5.QtGui import QIcon
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
        
        self.setWindowIcon(QIcon("assets/logo.png"))
        self.setWindowTitle("Organizador de tareas - ALACSA Tecnología y BlockChain")
        self.db_controller = SupabaseController()
        
        self.cargar_estilo()
        
        # --- AÑADIR LOGO Y CENTRAR TODO ---
        self.configurar_logo_centrado()
        
        self.configurar_conexiones()
        self.main_window = None
        
        if hasattr(self, 'Error'):
            self.Error.hide()

    def configurar_logo_centrado(self):
        """
        1. Añade un espaciador arriba.
        2. Añade el logo.
        3. Añade un espaciador abajo.
        Esto centra todo el contenido verticalmente.
        """
        logo_path = os.path.join(current_dir, "assets", "logo.png")
        layout = self.layout()
        
        if not layout: return

        # Solo aplicamos centrado vertical si el layout lo permite (ej. QVBoxLayout)
        es_vertical = isinstance(layout, QtWidgets.QVBoxLayout)

        # 1. MUELLE SUPERIOR (Empuja todo hacia abajo)
        if es_vertical:
            layout.insertStretch(0, 1)

        # 2. EL LOGO
        if os.path.exists(logo_path):
            self.lblLogo = QtWidgets.QLabel(self)
            self.lblLogo.setAlignment(QtCore.Qt.AlignCenter) # Centrar horizontalmente
            
            pixmap = QtGui.QPixmap(logo_path)
            if not pixmap.isNull():
                # Escalar si es muy grande (ej. 150px alto)
                if pixmap.height() > 150:
                    pixmap = pixmap.scaledToHeight(150, QtCore.Qt.SmoothTransformation)
                self.lblLogo.setPixmap(pixmap)
                
                # Insertar debajo del muelle superior (índice 1)
                # Si no es vertical, lo pone al principio (índice 0)
                idx = 1 if es_vertical else 0
                layout.insertWidget(idx, self.lblLogo)
                
                # Espacio fijo entre logo y formulario
                if es_vertical:
                    layout.insertSpacing(idx + 1, 30)

        # 3. MUELLE INFERIOR (Empuja todo hacia arriba)
        # Al tener muelle arriba y abajo con factor '1', se equilibra el espacio
        if es_vertical:
            layout.addStretch(1)

    def cargar_estilo(self):
        style_path = os.path.join(current_dir, "estilos", "brutalista_salmon.qss")
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                style = f.read()
                self.setStyleSheet(style)
        except Exception as e:
            print(f"Error cargando estilo: {e}")
    
    def configurar_conexiones(self):
        if hasattr(self, 'Primary'):
            self.Primary.clicked.connect(self.iniciar_sesion)
        
        if hasattr(self, 'btnInvitado'):
            self.btnInvitado.clicked.connect(self.entrar_como_invitado)
        
        if hasattr(self, 'Link'):
            self.Link.clicked.connect(self.crear_cuenta)
        
        if hasattr(self, 'txtUsuario'):
            self.txtUsuario.returnPressed.connect(self.iniciar_sesion)
        if hasattr(self, 'Contrasena'):
            self.Contrasena.returnPressed.connect(self.iniciar_sesion)
    
    def iniciar_sesion(self):
        email = self.txtUsuario.text().strip()
        password = self.Contrasena.text().strip()
        
        if not email or not password:
            self.mostrar_error("Por favor, completa todos los campos")
            return
        
        self.Primary.setEnabled(False)
        self.Primary.setText("Iniciando...")
        
        resultado = self.db_controller.iniciar_sesion(email, password)
        
        if resultado["success"]:
            user = self.db_controller.obtener_usuario_actual()
            username = user.username if user else email.split('@')[0]
            self.abrir_ventana_principal(username)
        else:
            error_msg = resultado.get("error", "Error desconocido")
            self.mostrar_error(error_msg)
            self.Primary.setEnabled(True)
            self.Primary.setText("Iniciar sesión")
    
    def entrar_como_invitado(self):
        self.abrir_ventana_principal("Invitado", modo_invitado=True)
    
    def crear_cuenta(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Crear Cuenta")
        dialog.setMinimumWidth(350)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
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
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_crear = QtWidgets.QPushButton("Crear cuenta")
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_layout.addWidget(btn_crear)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        btn_cancelar.clicked.connect(dialog.reject)
        
        def procesar_registro():
            email = txt_email.text().strip()
            username = txt_username.text().strip()
            password = txt_password.text()
            confirm = txt_confirm.text()
            
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
        dialog.exec_()
    
    def abrir_ventana_principal(self, username, modo_invitado=False):
        from main import MainWindow
        self.main_window = MainWindow()
        
        if not modo_invitado:
            # Inyectar controlador y recargar datos
            self.main_window.db_controller = self.db_controller
            self.main_window.cargar_tableros()
        
        if hasattr(self.main_window, 'current_user'):
            self.main_window.current_user.username = username
        
        if hasattr(self.main_window, 'lblUsuarioActual'):
            self.main_window.lblUsuarioActual.setText(f"Usuario: {username}")
        
        if hasattr(self.main_window, 'sesion_cerrada'):
            self.main_window.sesion_cerrada.connect(self.volver_al_login)
        
        self.main_window.show()
        self.hide()
    
    def volver_al_login(self):
        if self.db_controller:
            self.db_controller.cerrar_sesion()
        
        if hasattr(self, 'txtUsuario'): self.txtUsuario.clear()
        if hasattr(self, 'Contrasena'): self.Contrasena.clear()
        if hasattr(self, 'Error'): self.Error.hide()
        if hasattr(self, 'Primary'):
            self.Primary.setEnabled(True)
            self.Primary.setText("Iniciar sesión")
        
        self.show()
        if self.main_window:
            self.main_window.close()
            self.main_window = None
    
    def mostrar_error(self, mensaje):
        if hasattr(self, 'Error'):
            self.Error.setText(mensaje)
            self.Error.show()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())