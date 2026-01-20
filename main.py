import sys
import os
from PyQt5 import QtWidgets, uic
from Controladores.Modelos import Tablero, User
from Controladores.Listas import ListasController

# Ensure we can find the UI file
current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "Pantallas", "Login.ui")

class ListasWindow(QtWidgets.QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("MiniTrello - Listas")
        self.resize(800, 600)
        
        self.layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel(f"Tablero: {self.controller.tablero.name}")
        self.layout.addWidget(self.label)
        
        # Placeholder for lists display
        self.lists_label = QtWidgets.QLabel("Aquí aparecerán tus listas (Implementación pendiente de UI)")
        self.layout.addWidget(self.lists_label)
        
        self.setLayout(self.layout)

class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        try:
            uic.loadUi(ui_path, self)
        except FileNotFoundError:
            print(f"Error: Could not find UI file at {ui_path}")
            sys.exit(1)
            
        self.btnLogin.clicked.connect(self.open_lists)
        # Initialize controller with dummy data for now
        self.user = User("Usuario", "usuario@ejemplo.com")
        self.tablero = Tablero("Mi Tablero", self.user)
        self.controller = ListasController(self.tablero)

    def open_lists(self):
        # In a real app, we would validate credentials here
        print("Iniciando sesión...")
        self.listas_window = ListasWindow(self.controller)
        self.listas_window.show()
        self.close()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
