import os
import sys
from PyQt5 import QtWidgets, uic


def cargar_estilos(app):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    qss_path = os.path.join(base_dir, "estilos", "EstiloDefalt.qss")
    with open(qss_path, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())


class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(base_dir, "Pantallas", "Login.ui")
        uic.loadUi(ui_path, self)

        self.btnInvitado.clicked.connect(self.entrar_invitado)

    def entrar_invitado(self):
        self.app = AppWindow("Invitado")
        self.app.show()
        self.close()


class AppWindow(QtWidgets.QWidget):
    def __init__(self, usuario):
        super().__init__()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(base_dir, "Pantallas", "App.ui")
        uic.loadUi(ui_path, self)

        self.lblUsuarioActual.setText(f"Usuario: {usuario}")
        self.pestanasPrincipal.setCurrentIndex(0)

        self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
        self.btnVolverATableros.clicked.connect(lambda: self.pestanasPrincipal.setCurrentIndex(0))
        self.btnAbrirTablero.clicked.connect(self.abrir_tablero)

    def cerrar_sesion(self):
        self.login = LoginWindow()
        self.login.show()
        self.close()

    def abrir_tablero(self):
        item = self.listaTableros.currentItem()
        if item:
            self.lblNombreTablero.setText(f"Tablero: {item.text()}")
            self.pestanasPrincipal.setCurrentIndex(1)


def main():
    app = QtWidgets.QApplication(sys.argv)
    cargar_estilos(app)
    ventana = LoginWindow()
    ventana.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
