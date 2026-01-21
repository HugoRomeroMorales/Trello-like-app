import sys
import os
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from Controladores.Modelos import Tablero, User
from Controladores.Listas import ListasController
from Controladores.Controller_BD import SupabaseController

# Ensure we can find the UI file
current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "Pantallas", "App.ui")

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        try:
            uic.loadUi(ui_path, self)
        except FileNotFoundError:
            print(f"Error: Could not find UI file at {ui_path}")
            sys.exit(1)

        # Default Theme
        self.tema_actual = "brutalista" 
        self.cargar_tema(self.tema_actual)

        # Initialize DB Controller
        # NOTE: User should set SUPABASE_URL and SUPABASE_KEY env vars or we can prompt/hardcode for testing
        self.db_controller = SupabaseController()
        
        # Mock user for now
        self.current_user = User(username="UsuarioDemo")
        
        # Setup UI connections
        self.configurar_conexiones()
        
        # Setup Header for Theme Toggle (if possible, or just a button somewhere accessible)
        # We can add a toggle button programmatically to the layout if needed.
        # Let's add a button to the list of boards for now or top right corner if layout permits.
        
        # Initial state
        self.pestanasPrincipal.setCurrentIndex(0) # Tableros tab
        self.cargar_tableros()

    def cargar_tema(self, nombre_tema):
        if nombre_tema == "oscuro":
            filename = "trello_oscuro.qss"
        elif nombre_tema == "claro":
             filename = "trello_claro.qss"
        else:
             filename = "brutalista_salmon.qss"

        path = os.path.join(current_dir, "estilos", filename)
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                style = f.read()
                self.setStyleSheet(style)
        except Exception as e:
            print(f"Error cargando tema {nombre_tema}: {e}")

    def configurar_conexiones(self):
        # Tableros Tab
        self.btnNuevoTablero.clicked.connect(self.crear_tablero)
        self.btnAbrirTablero.clicked.connect(self.abrir_tablero_seleccionado)
        self.listaTableros.itemDoubleClicked.connect(self.abrir_tablero_seleccionado)
        
        # Settings Tab - Theme Combo
        # Check if comboTema exists (it should from UI file)
        if hasattr(self, 'comboTema'):
            self.comboTema.clear()
            self.comboTema.addItems(["Modo Oscuro", "Modo Claro", "Brutalista Salmón"])
            self.comboTema.currentIndexChanged.connect(self.al_cambiar_tema)
            
            # Set initial state
            if self.tema_actual == "oscuro":
                self.comboTema.setCurrentIndex(0)
            elif self.tema_actual == "claro":
                self.comboTema.setCurrentIndex(1)
            else:
                 self.comboTema.setCurrentIndex(2)

        # Tablero Tab
        self.btnVolverATableros.clicked.connect(self.volver_a_tableros)
        self.btnNuevaColumna.clicked.connect(self.crear_nueva_lista)
        self.btnNuevaTarjeta.clicked.connect(self.crear_nueva_tarjeta)

    def al_cambiar_tema(self, index):
        if index == 0:
            self.cargar_tema("oscuro")
            self.tema_actual = "oscuro"
        elif index == 1:
            self.cargar_tema("claro")
            self.tema_actual = "claro"
        elif index == 2:
            self.cargar_tema("brutalista")
            self.tema_actual = "brutalista"

    def cargar_tableros(self):
        self.listaTableros.clear()
        self.tableros = self.db_controller.obtener_tableros()
        for tablero in self.tableros:
            self.listaTableros.addItem(f"{tablero.titulo} ({tablero.get_card_count()} tarjetas)")

    def crear_tablero(self):
        titulo, ok = QtWidgets.QInputDialog.getText(self, "Nuevo Tablero", "Nombre del tablero:")
        if ok and titulo:
            new_board = self.db_controller.crear_tablero(titulo)
            if new_board:
                self.cargar_tableros()

    def abrir_tablero_seleccionado(self):
        current_row = self.listaTableros.currentRow()
        if current_row >= 0 and current_row < len(self.tableros):
            self.mostrar_tablero(self.tableros[current_row])

    def mostrar_tablero(self, tablero):
        self.current_tablero = tablero
        self.listas_controller = ListasController(self.current_tablero, self.db_controller)
        
        self.lblNombreTablero.setText(f"Tablero: {tablero.titulo}")
        self.pestanasPrincipal.setCurrentIndex(1) # Tablero tab
        
        self.renderizar_columnas()

    def renderizar_columnas(self):
        # Clear existing columns in the layout
        # Note: This is a bit tricky with the existing static layout in App.ui
        # The UI has 'columnaPorHacer', 'columnaEnProgreso', 'columnaHecho' hardcoded.
        # We should probably hide them and create new ones dynamically, or reuse them if they match.
        # For this adaptation, let's try to map the first 3 lists to these columns, and hide the rest/create new ones if needed.
        # But to be proper dynamic, we should clear the layoutColumnas and rebuild.
        
        # For simplicity in this step, let's clear the layout and rebuild using the style of the hardcoded ones.
        
        # First, remove all items from layoutColumnas
        while self.layoutColumnas.count():
            item = self.layoutColumnas.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                
        # Now add columns for each list
        listas = self.listas_controller.obtener_listas()
        for lista in listas:
            self.agregar_columna_ui(lista)
            
        # Add spacer at the end
        spacer = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.layoutColumnas.addItem(spacer)

    def agregar_columna_ui(self, lista):
        # Create a widget similar to the hardcoded columns
        frame = QtWidgets.QFrame()
        frame.setMinimumWidth(300)
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        layout = QtWidgets.QVBoxLayout(frame)
        
        # Header (Label)
        lbl = QtWidgets.QLabel(lista.titulo)
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        lbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # Use functools.partial or lambda with default arg to capture 'lista' correctly if loop involved, 
        # but here 'lista' is local args so lambda is fine.
        lbl.customContextMenuRequested.connect(lambda pos, l=lista: self.mostrar_menu_lista(pos, lbl, l))
        layout.addWidget(lbl)
        
        # List Widget (Cards)
        list_widget = QtWidgets.QListWidget()
        list_widget.setProperty("list_id", lista.id)
        list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        list_widget.customContextMenuRequested.connect(lambda pos, lw=list_widget, lid=lista.id: self.mostrar_menu_tarjeta(pos, lw, lid))

        for card in lista.cards:
            item = QtWidgets.QListWidgetItem(card.titulo)
            item.setData(QtCore.Qt.UserRole, card.id) # Store card ID
            list_widget.addItem(item)
            
        layout.addWidget(list_widget)
        
        self.layoutColumnas.addWidget(frame)

    def mostrar_menu_lista(self, pos, label_widget, lista):
        menu = QtWidgets.QMenu()
        action_rename = menu.addAction("Renombrar Lista")
        action_delete = menu.addAction("Eliminar Lista")
        
        action = menu.exec_(label_widget.mapToGlobal(pos))
        
        if action == action_rename:
            new_name, ok = QtWidgets.QInputDialog.getText(self, "Renombrar Lista", "Nuevo nombre:", text=lista.titulo)
            if ok and new_name:
                if self.listas_controller.renombrar_lista(lista.id, new_name):
                    self.renderizar_columnas()
                    
        elif action == action_delete:
            confirm = QtWidgets.QMessageBox.question(self, "Confirmar", f"¿Eliminar lista '{lista.titulo}'?", 
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if confirm == QtWidgets.QMessageBox.Yes:
                if self.listas_controller.eliminar_lista(lista.id):
                    self.renderizar_columnas()

    def mostrar_menu_tarjeta(self, pos, list_widget, list_id):
        item = list_widget.itemAt(pos)
        if not item: return
        
        menu = QtWidgets.QMenu()
        action_delete = menu.addAction("Eliminar Tarjeta")
        
        action = menu.exec_(list_widget.mapToGlobal(pos))
        
        if action == action_delete:
            card_id = item.data(QtCore.Qt.UserRole)
            if self.listas_controller.eliminar_tarjeta(list_id, card_id):
                self.renderizar_columnas()

    def crear_nueva_lista(self):
        if not hasattr(self, 'current_tablero'): return
        
        titulo, ok = QtWidgets.QInputDialog.getText(self, "Nueva Lista", "Nombre de la lista:")
        if ok and titulo:
            self.listas_controller.crear_lista(titulo)
            self.renderizar_columnas()

    def crear_nueva_tarjeta(self):
        if not hasattr(self, 'listas_controller'):
             return

        # For simplicity, add to the first list or ask user which list
        listas = self.listas_controller.obtener_listas()
        if not listas:
            QtWidgets.QMessageBox.warning(self, "Error", "No hay listas en este tablero")
            return
            
        # Ask for list
        list_names = [l.titulo for l in listas]
        list_name, ok = QtWidgets.QInputDialog.getItem(self, "Nueva Tarjeta", "Seleccionar lista:", list_names, 0, False)
        if ok and list_name:
            # Find list object
            target_list = next((l for l in listas if l.titulo == list_name), None)
            if target_list:
                titulo, ok = QtWidgets.QInputDialog.getText(self, "Nueva Tarjeta", "Título de la tarjeta:")
                if ok and titulo:
                    self.listas_controller.agregar_tarjeta(target_list.id, titulo)
                    self.renderizar_columnas()

    def volver_a_tableros(self):
        self.pestanasPrincipal.setCurrentIndex(0)
        self.cargar_tableros()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

