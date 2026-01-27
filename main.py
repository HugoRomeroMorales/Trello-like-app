import sys
import os
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from Controladores.Modelos import Tablero, User
from Controladores.Listas import ListasController
from Controladores.Controller_BD import SupabaseController

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "Pantallas", "App.ui")

# --- DIÁLOGO DE DETALLES Y ASIGNACIÓN (NUEVO) ---
class TarjetaDetalleDialog(QtWidgets.QDialog):
    def __init__(self, tarjeta, controller, list_id, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.tarjeta = tarjeta
        self.list_id = list_id
        self.setWindowTitle("Detalles de la Tarjeta")
        self.setMinimumSize(500, 450)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # 1. Título y Descripción
        group_info = QtWidgets.QGroupBox("Información")
        form_layout = QtWidgets.QFormLayout(group_info)
        
        self.txt_titulo = QtWidgets.QLineEdit(tarjeta.titulo)
        form_layout.addRow("Título:", self.txt_titulo)
        
        self.txt_descripcion = QtWidgets.QPlainTextEdit(tarjeta.descripcion)
        self.txt_descripcion.setPlaceholderText("Añade una descripción...")
        self.txt_descripcion.setMinimumHeight(100)
        form_layout.addRow("Descripción:", self.txt_descripcion)
        
        main_layout.addWidget(group_info)
        
        # 2. Asignación de Usuarios
        group_assign = QtWidgets.QGroupBox("Usuarios Asignados")
        assign_layout = QtWidgets.QVBoxLayout(group_assign)
        
        # Barra para añadir
        add_layout = QtWidgets.QHBoxLayout()
        self.combo_users = QtWidgets.QComboBox()
        users = self.controller.obtener_todos_usuarios()
        for u in users:
            self.combo_users.addItem(u.username, u.id)
            
        btn_asignar = QtWidgets.QPushButton("Asignar")
        btn_asignar.clicked.connect(self.asignar_usuario)
        btn_asignar.setStyleSheet("background-color: #e0e0e0; color: black; border-radius: 4px; padding: 5px;")
        
        add_layout.addWidget(self.combo_users)
        add_layout.addWidget(btn_asignar)
        assign_layout.addLayout(add_layout)
        
        # Lista de asignados
        self.list_assigned = QtWidgets.QListWidget()
        self.list_assigned.setFixedHeight(80)
        assign_layout.addWidget(self.list_assigned)
        
        # Botón quitar
        btn_quitar = QtWidgets.QPushButton("Quitar Seleccionado")
        btn_quitar.clicked.connect(self.quitar_usuario)
        btn_quitar.setStyleSheet("color: red; border: 1px solid #ffcccc; border-radius: 4px;")
        assign_layout.addWidget(btn_quitar)
        
        main_layout.addWidget(group_assign)
        
        self.refrescar_lista_asignados()

        # Botones Finales
        btn_layout = QtWidgets.QHBoxLayout()
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        self.btn_guardar = QtWidgets.QPushButton("Guardar Cambios")
        self.btn_guardar.setStyleSheet("background-color: #FA8072; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_guardar.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        main_layout.addLayout(btn_layout)

    def refrescar_lista_asignados(self):
        self.list_assigned.clear()
        for u in self.tarjeta.assignees:
            self.list_assigned.addItem(f"👤 {u.username}")

    def asignar_usuario(self):
        uid = self.combo_users.currentData()
        if not uid or any(u.id == uid for u in self.tarjeta.assignees): return
        if self.controller.gestionar_asignacion(self.list_id, self.tarjeta.id, uid, True):
            self.refrescar_lista_asignados()

    def quitar_usuario(self):
        row = self.list_assigned.currentRow()
        if row < 0: return
        user = self.tarjeta.assignees[row]
        if self.controller.gestionar_asignacion(self.list_id, self.tarjeta.id, user.id, False):
            self.refrescar_lista_asignados()

    def get_data(self):
        return self.txt_titulo.text(), self.txt_descripcion.toPlainText()


class ListaDragDrop(QtWidgets.QListWidget):
    cardMoved = QtCore.pyqtSignal(str, str, str)

    def __init__(self, list_id, parent=None):
        super().__init__(parent)
        self.list_id = list_id
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)

    def dropEvent(self, event):
        source_widget = event.source()
        if not isinstance(source_widget, ListaDragDrop):
            event.ignore()
            return
        item = source_widget.currentItem()
        if item:
            card_id = item.data(QtCore.Qt.UserRole)
            if source_widget != self:
                self.cardMoved.emit(source_widget.list_id, self.list_id, card_id)
        event.accept()


        
class PapeleraTablerosDialog(QtWidgets.QDialog):
    def __init__(self, db_controller, parent=None):
        super().__init__(parent)
        self.db = db_controller
        self.setWindowTitle("Papelera de Tableros")
        self.setMinimumSize(400, 300)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Tableros Eliminados"))

        self.lista = QtWidgets.QListWidget()
        layout.addWidget(self.lista)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_restaurar = QtWidgets.QPushButton("♻ Restaurar")
        btn_restaurar.clicked.connect(self.restaurar)
        btn_borrar = QtWidgets.QPushButton("🔥 Borrar Definitivamente")
        btn_borrar.clicked.connect(self.borrar_final)
        
        btn_layout.addWidget(btn_restaurar)
        btn_layout.addWidget(btn_borrar)
        layout.addLayout(btn_layout)
        
        self.cargar()

    def cargar(self):
        self.lista.clear()
        self.tableros = self.db.obtener_papelera_tableros()
        for t in self.tableros:
            item = QtWidgets.QListWidgetItem(f"📁 {t.titulo}")
            item.setData(QtCore.Qt.UserRole, t.id)
            self.lista.addItem(item)

    def restaurar(self):
        row = self.lista.currentRow()
        if row < 0: return
        tid = self.lista.currentItem().data(QtCore.Qt.UserRole)
        if self.db.restaurar_tablero(tid):
            self.cargar()
            self.parent().cargar_tableros() # Refrescar ventana principal
            QtWidgets.QMessageBox.information(self, "Listo", "Tablero restaurado")

    def borrar_final(self):
        row = self.lista.currentRow()
        if row < 0: return
        if QtWidgets.QMessageBox.question(self, "Ojo", "¿Borrar para siempre?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            tid = self.lista.currentItem().data(QtCore.Qt.UserRole)
            if self.db.eliminar_tablero_definitivamente(tid): self.cargar()

    def cargar_datos(self):
        self.lista_papelera.clear()
        self.items_data = self.controller.obtener_papelera() # Guardamos los objetos reales
        
        if not self.items_data:
            self.lista_papelera.addItem("La papelera está vacía")
            self.btn_restaurar.setEnabled(False)
            self.btn_borrar.setEnabled(False)
            return

        self.btn_restaurar.setEnabled(True)
        self.btn_borrar.setEnabled(True)

        for card in self.items_data:
            item = QtWidgets.QListWidgetItem(f"{card.titulo}")
            item.setData(QtCore.Qt.UserRole, card.id)
            self.lista_papelera.addItem(item)

    def restaurar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0: return
        card_id = self.lista_papelera.currentItem().data(QtCore.Qt.UserRole)
        
        if self.controller.restaurar_tarjeta(card_id):
            QtWidgets.QMessageBox.information(self, "Éxito", "Tarjeta restaurada al tablero")
            self.cargar_datos() # Recargar lista
            self.parent().renderizar_columnas() # Actualizar tablero principal (truco)
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "No se pudo restaurar")

    def borrar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0: return
        card_id = self.lista_papelera.currentItem().data(QtCore.Qt.UserRole)
        
        confirm = QtWidgets.QMessageBox.question(self, "Confirmar", "¿Borrar para siempre? No se podrá deshacer.", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if confirm == QtWidgets.QMessageBox.Yes:
            if self.controller.eliminar_definitivamente(card_id):
                self.cargar_datos()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo eliminar")


class PapeleraListasDialog(QtWidgets.QDialog):
    """Diálogo para gestionar columnas/listas eliminadas."""
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Papelera de Columnas")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: #ffffff;")

        layout = QtWidgets.QVBoxLayout(self)

        lbl = QtWidgets.QLabel("Columnas Eliminadas")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(lbl)

        # Lista de columnas eliminadas
        self.lista_papelera = QtWidgets.QListWidget()
        self.lista_papelera.setStyleSheet("""
            QListWidget { border: 1px solid #ccc; border-radius: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #eee; }
        """)
        layout.addWidget(self.lista_papelera)

        # Botones de acción
        btn_layout = QtWidgets.QHBoxLayout()
        
        self.btn_restaurar = QtWidgets.QPushButton("♻ Restaurar")
        self.btn_restaurar.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        self.btn_restaurar.clicked.connect(self.restaurar_seleccionada)
        
        self.btn_borrar = QtWidgets.QPushButton("🔥 Eliminar Definitivamente")
        self.btn_borrar.setStyleSheet("background-color: #f44336; color: white; padding: 8px; font-weight: bold;")
        self.btn_borrar.clicked.connect(self.borrar_seleccionada)
        
        btn_cerrar = QtWidgets.QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_restaurar)
        btn_layout.addWidget(self.btn_borrar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

        self.cargar_datos()

    def cargar_datos(self):
        self.lista_papelera.clear()
        self.items_data = self.controller.obtener_papelera_listas()
        
        if not self.items_data:
            self.lista_papelera.addItem("La papelera está vacía")
            self.btn_restaurar.setEnabled(False)
            self.btn_borrar.setEnabled(False)
            return

        self.btn_restaurar.setEnabled(True)
        self.btn_borrar.setEnabled(True)

        for lista in self.items_data:
            texto = f"📋 {lista.titulo}"
            item = QtWidgets.QListWidgetItem(texto)
            item.setData(QtCore.Qt.UserRole, lista.id)
            self.lista_papelera.addItem(item)

    def restaurar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0: return
        
        item = self.lista_papelera.currentItem()
        if not item: return
        list_id = item.data(QtCore.Qt.UserRole)
        
        if self.controller.restaurar_lista_papelera(list_id):
            QtWidgets.QMessageBox.information(self, "Éxito", "Columna restaurada al tablero")
            self.cargar_datos()
            if self.parent():
                self.parent().renderizar_columnas()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "No se pudo restaurar")

    def borrar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0: return
        
        item = self.lista_papelera.currentItem()
        if not item: return
        list_id = item.data(QtCore.Qt.UserRole)
        
        confirm = QtWidgets.QMessageBox.question(
            self, 
            "Confirmar", 
            "¿Borrar esta columna para siempre? Se perderán todas sus tarjetas. No se podrá deshacer.", 
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if confirm == QtWidgets.QMessageBox.Yes:
            if self.controller.eliminar_lista_definitivamente(list_id):
                self.cargar_datos()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo eliminar")


class PapeleraDialog(QtWidgets.QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Papelera de Reciclaje")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: #ffffff;")

        layout = QtWidgets.QVBoxLayout(self)

        lbl = QtWidgets.QLabel("Tarjetas Eliminadas")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(lbl)

        # Lista de elementos eliminados
        self.lista_papelera = QtWidgets.QListWidget()
        self.lista_papelera.setStyleSheet("""
            QListWidget { border: 1px solid #ccc; border-radius: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #eee; }
        """)
        layout.addWidget(self.lista_papelera)

        # Botones de acción
        btn_layout = QtWidgets.QHBoxLayout()
        
        self.btn_restaurar = QtWidgets.QPushButton("♻ Restaurar")
        self.btn_restaurar.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        # Aquí daba el error porque no encontraba la función de abajo
        self.btn_restaurar.clicked.connect(self.restaurar_seleccionada)
        
        self.btn_borrar = QtWidgets.QPushButton("🔥 Eliminar Definitivamente")
        self.btn_borrar.setStyleSheet("background-color: #f44336; color: white; padding: 8px; font-weight: bold;")
        self.btn_borrar.clicked.connect(self.borrar_seleccionada)
        
        btn_cerrar = QtWidgets.QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_restaurar)
        btn_layout.addWidget(self.btn_borrar)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

        self.cargar_datos()

    def cargar_datos(self):
        self.lista_papelera.clear()
        # Obtenemos los objetos reales de la papelera
        self.items_data = self.controller.obtener_papelera() 
        
        if not self.items_data:
            self.lista_papelera.addItem("La papelera está vacía")
            self.btn_restaurar.setEnabled(False)
            self.btn_borrar.setEnabled(False)
            return

        self.btn_restaurar.setEnabled(True)
        self.btn_borrar.setEnabled(True)

        for card in self.items_data:
            # Mostramos Título (y lista origen si quieres)
            texto = f"{card.titulo}"
            item = QtWidgets.QListWidgetItem(texto)
            # Guardamos el ID oculto para saber cuál borrar/restaurar
            item.setData(QtCore.Qt.UserRole, card.id)
            self.lista_papelera.addItem(item)

    def restaurar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0: return # No hay nada seleccionado
        
        # Recuperamos el ID oculto
        item = self.lista_papelera.currentItem()
        if not item: return
        card_id = item.data(QtCore.Qt.UserRole)
        
        if self.controller.restaurar_tarjeta(card_id):
            QtWidgets.QMessageBox.information(self, "Éxito", "Tarjeta restaurada al tablero")
            self.cargar_datos() # Recargar la lista de la papelera
            # Truco: Actualizar el tablero principal que está detrás
            if self.parent():
                self.parent().renderizar_columnas()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "No se pudo restaurar")

    def borrar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0: return
        
        item = self.lista_papelera.currentItem()
        if not item: return
        card_id = item.data(QtCore.Qt.UserRole)
        
        confirm = QtWidgets.QMessageBox.question(
            self, 
            "Confirmar", 
            "¿Borrar para siempre? No se podrá deshacer.", 
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if confirm == QtWidgets.QMessageBox.Yes:
            if self.controller.eliminar_definitivamente(card_id):
                self.cargar_datos()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo eliminar")
class MainWindow(QtWidgets.QWidget):
    sesion_cerrada = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        try:
            uic.loadUi(ui_path, self)
        except FileNotFoundError:
            print(f"Error: Could not find UI file at {ui_path}")
            sys.exit(1)

        self.tema_actual = "brutalista"
        self.cargar_tema(self.tema_actual)
        self.db_controller = SupabaseController()
        self.current_user = User(username="UsuarioDemo")
        self.configurar_conexiones()
        self.pestanasPrincipal.setCurrentIndex(0)
        self.cargar_tableros()

    def cargar_tema(self, nombre_tema):
        filename = "trello_oscuro.qss" if nombre_tema == "oscuro" else "trello_claro.qss" if nombre_tema == "claro" else "brutalista_salmon.qss"
        path = os.path.join(current_dir, "estilos", filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Error cargando tema: {e}")

    def configurar_conexiones(self):
        self.btnNuevoTablero.clicked.connect(self.crear_tablero)
        self.btnAbrirTablero.clicked.connect(self.abrir_tablero_seleccionado)
        self.btnBorrarTablero.clicked.connect(self.borrar_tablero_seleccionado)
        self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
        self.listaTableros.itemDoubleClicked.connect(self.abrir_tablero_seleccionado)
        self.btnNuevoTablero.clicked.connect(self.crear_tablero)
        self.txtBuscarTarjetas.textChanged.connect(self.buscar_tarjetas)

        if hasattr(self, "comboTema"):
            self.comboTema.clear()
            self.comboTema.addItems(["Modo Oscuro", "Modo Claro", "Brutalista Salmón"])
            self.comboTema.currentIndexChanged.connect(self.al_cambiar_tema)
            self.comboTema.setCurrentIndex(0 if self.tema_actual == "oscuro" else 1 if self.tema_actual == "claro" else 2)

        if hasattr(self, "chkAutoGuardado"):
            self.chkAutoGuardado.stateChanged.connect(self.alternar_autoguardado)

        if not hasattr(self, 'btnPapeleraTableros'):
            # Buscamos el layout donde están los botones de tableros
            # Normalmente btnNuevoTablero está en un layout horizontal
            parent_layout = self.btnNuevoTablero.parentWidget().layout()
            
            self.btnPapeleraTableros = QtWidgets.QPushButton("🗑 Papelera Tableros")
            self.btnPapeleraTableros.setCursor(QtCore.Qt.PointingHandCursor)
            self.btnPapeleraTableros.setStyleSheet("background-color: #ECEFF1; color: #455A64; border: 1px solid #CFD8DC; padding: 6px; font-weight: bold;")
            self.btnPapeleraTableros.clicked.connect(self.abrir_papelera_tableros)

        self.btnVolverATableros.clicked.connect(self.volver_a_tableros)
        self.btnNuevaColumna.clicked.connect(self.crear_nueva_lista)
        self.btnNuevaTarjeta.clicked.connect(self.crear_nueva_tarjeta)
        self.btnGuardarTablero.clicked.connect(self.guardar_tablero)
        self.txtBuscarTarjetas.textChanged.connect(self.buscar_tarjetas)
        parent_layout.addWidget(self.btnPapeleraTableros)

    def al_cambiar_tema(self, index):
        temas = ["oscuro", "claro", "brutalista"]
        self.tema_actual = temas[index]
        self.cargar_tema(self.tema_actual)
        self._refrescar_estilos()

    def _refrescar_estilos(self):
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def cargar_tableros(self):
        self.listaTableros.clear()
        try:
            self.tableros = self.db_controller.obtener_tableros()
            if not self.tableros:
                self.listaTableros.addItem("No hay tableros. Crea uno nuevo!")
            else:
                for tablero in self.tableros:
                    self.listaTableros.addItem(f"{tablero.titulo} ({tablero.get_card_count()} tarjetas)")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Error al cargar tableros: {e}")
            self.tableros = []

    def crear_tablero(self):
        titulo, ok = QtWidgets.QInputDialog.getText(self, "Nuevo Tablero", "Nombre del tablero:")
        if ok and titulo:
            if self.db_controller.crear_tablero(titulo):
                self.cargar_tableros()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo crear el tablero.")

    def abrir_tablero_seleccionado(self):
        row = self.listaTableros.currentRow()
        if 0 <= row < len(self.tableros):
            self.mostrar_tablero(self.tableros[row])

    def mostrar_tablero(self, tablero):
        self.current_tablero = tablero
        self.listas_controller = ListasController(self.current_tablero, self.db_controller)
        # IMPORTANTE: Cargar asignados
        self.listas_controller.cargar_asignados_iniciales()
        
        self.lblNombreTablero.setText(f"Tablero: {tablero.titulo}")
        self.pestanasPrincipal.setCurrentIndex(1)
        self.renderizar_columnas()
        
        self.listas_controller.cargar_asignados_iniciales()
        
        self.lblNombreTablero.setText(f"Tablero: {tablero.titulo}")
        self.pestanasPrincipal.setCurrentIndex(1)
        
        # --- INYECTAR BOTÓN DE PAPELERA (Si no existe ya) ---
        if not hasattr(self, 'btnPapelera'):
            # Buscamos el layout donde están los otros botones (Volver, Guardar, etc.)
            # Normalmente están junto a btnVolverATableros
            parent_layout = self.btnVolverATableros.parentWidget().layout()
            
            self.btnPapelera = QtWidgets.QPushButton("🗑 Papelera Tarjetas")
            self.btnPapelera.setCursor(QtCore.Qt.PointingHandCursor)
            # Estilo rojo suave para diferenciar
            self.btnPapelera.setStyleSheet("background-color: #FFEBEE; color: #D32F2F; border: 1px solid #FFCDD2; padding: 5px 10px; border-radius: 4px; font-weight: bold;")
            self.btnPapelera.clicked.connect(self.abrir_papelera)
            
            # Botón de papelera de columnas
            self.btnPapeleraColumnas = QtWidgets.QPushButton("🗑 Papelera Columnas")
            self.btnPapeleraColumnas.setCursor(QtCore.Qt.PointingHandCursor)
            self.btnPapeleraColumnas.setStyleSheet("background-color: #E8F5E9; color: #388E3C; border: 1px solid #C8E6C9; padding: 5px 10px; border-radius: 4px; font-weight: bold;")
            self.btnPapeleraColumnas.clicked.connect(self.abrir_papelera_columnas)
            
            # Lo añadimos antes del botón "Volver" (índice -1 o insertWidget)
            # Si no quieres complicarte con índices, simplemente addWidget
            parent_layout.insertWidget(parent_layout.count() - 1, self.btnPapelera)
            parent_layout.insertWidget(parent_layout.count() - 1, self.btnPapeleraColumnas)
        # ----------------------------------------------------

        self.renderizar_columnas()

    # --- MÉTODOS PARA ABRIR LAS PAPELERAS ---
    def abrir_papelera(self):
        if not hasattr(self, 'listas_controller'): return
        dialog = PapeleraDialog(self.listas_controller, self)
        dialog.exec_()

    def abrir_papelera_columnas(self):
        """Abre la papelera de columnas/listas eliminadas."""
        if not hasattr(self, 'listas_controller'): return
        dialog = PapeleraListasDialog(self.listas_controller, self)
        dialog.exec_()

    def renderizar_columnas(self):
        while self.layoutColumnas.count():
            item = self.layoutColumnas.takeAt(0)
            if item.widget(): item.widget().setParent(None)

        for lista in self.listas_controller.obtener_listas():
            self.agregar_columna_ui(lista)

        self.layoutColumnas.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

    def agregar_columna_ui(self, lista):
        frame = QtWidgets.QFrame()
        frame.setMinimumWidth(340)
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setObjectName("columnaFrame")

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Cabecera
        header = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(lista.titulo)
        lbl.setObjectName("lblColumnaHeader")
        header.addWidget(lbl)

        btn_edit = QtWidgets.QPushButton("✎")
        btn_edit.setFixedSize(40, 40)
        btn_edit.setCursor(QtCore.Qt.PointingHandCursor)
        btn_edit.setObjectName("btnColumnaHeader")
        btn_edit.clicked.connect(lambda _, l=lista: self.renombrar_lista_ui(l))
        header.addWidget(btn_edit)

        btn_del = QtWidgets.QPushButton("🗑")
        btn_del.setFixedSize(40, 40)
        btn_del.setCursor(QtCore.Qt.PointingHandCursor)
        btn_del.setObjectName("btnColumnaHeader")
        btn_del.clicked.connect(lambda _, l=lista: self.eliminar_lista_ui(l))
        header.addWidget(btn_del)
        layout.addLayout(header)

        # Lista
        list_widget = ListaDragDrop(lista.id)
        list_widget.setSpacing(10)
        list_widget.setObjectName("listaTarjetas")
        list_widget.cardMoved.connect(self.procesar_movimiento_tarjeta)
        # Conectar Doble Clic para editar detalles
        list_widget.itemDoubleClicked.connect(self.abrir_detalles_tarjeta)
        
        list_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        list_widget.setMinimumHeight(200)
        list_widget.setUniformItemSizes(False)

        for card in lista.cards:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, card.id)
            item.setText("") 
            
            card_widget = QtWidgets.QFrame()
            card_widget.setObjectName("cardBody")
            card_widget.setMinimumHeight(80)

            card_layout = QtWidgets.QHBoxLayout(card_widget)
            card_layout.setContentsMargins(15, 10, 15, 10)
            
            # Título
            lbl_card = QtWidgets.QLabel(str(card.titulo))
            lbl_card.setWordWrap(True)
            lbl_card.setObjectName("lblCardTitle")
            card_layout.addWidget(lbl_card, 1)

            # Asignados (Bolitas)
            if card.assignees:
                assign_layout = QtWidgets.QHBoxLayout()
                assign_layout.setSpacing(-8)
                for u in card.assignees[:3]:
                    inicial = u.username[0].upper() if u.username else "?"
                    lbl_user = QtWidgets.QLabel(inicial)
                    lbl_user.setFixedSize(26, 26)
                    lbl_user.setAlignment(QtCore.Qt.AlignCenter)
                    lbl_user.setStyleSheet("background-color: #172b4d; color: white; border-radius: 13px; font-weight: bold; font-size: 11px; border: 1px solid white;")
                    assign_layout.addWidget(lbl_user)
                card_layout.addLayout(assign_layout)

            # Botones tarjeta
            btn_edit_c = QtWidgets.QPushButton("✎")
            btn_edit_c.setFixedSize(40, 40)
            btn_edit_c.setObjectName("btnCardAction")
            btn_edit_c.clicked.connect(lambda _, l_id=lista.id, c=card: self.renombrar_tarjeta_ui(l_id, c))
            card_layout.addWidget(btn_edit_c)

            btn_del_c = QtWidgets.QPushButton("🗑")
            btn_del_c.setFixedSize(40, 40)
            btn_del_c.setObjectName("btnCardAction")
            btn_del_c.clicked.connect(lambda _, l_id=lista.id, c_id=card.id: self.eliminar_tarjeta_ui(l_id, c_id))
            card_layout.addWidget(btn_del_c)

            item.setSizeHint(card_widget.sizeHint())
            list_widget.addItem(item)
            list_widget.setItemWidget(item, card_widget)

        layout.addWidget(list_widget)
        self.layoutColumnas.addWidget(frame)

    def abrir_detalles_tarjeta(self, item):
        card_id = item.data(QtCore.Qt.UserRole)
        list_id = self.sender().list_id
        
        lista_obj = next((l for l in self.listas_controller.obtener_listas() if l.id == list_id), None)
        if not lista_obj: return
        tarjeta_obj = next((c for c in lista_obj.cards if c.id == card_id), None)
        if not tarjeta_obj: return

        dialog = TarjetaDetalleDialog(tarjeta_obj, self.listas_controller, list_id, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            title, desc = dialog.get_data()
            if title != tarjeta_obj.titulo or desc != tarjeta_obj.descripcion:
                if self.listas_controller.actualizar_contenido_tarjeta(list_id, card_id, title, desc):
                    self.renderizar_columnas()

    def procesar_movimiento_tarjeta(self, sid, did, cid):
        if self.listas_controller.mover_tarjeta(sid, did, cid):
            self.renderizar_columnas()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Fallo al mover")

    def renombrar_lista_ui(self, lista):
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Renombrar", "Nombre:", text=lista.titulo)
        if ok and new_name and self.listas_controller.renombrar_lista(lista.id, new_name):
            self.renderizar_columnas()

    def eliminar_lista_ui(self, lista):
        if QtWidgets.QMessageBox.question(self, "Confirmar", "¿Eliminar lista?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            if self.listas_controller.eliminar_lista(lista.id): self.renderizar_columnas()

    def renombrar_tarjeta_ui(self, lid, card):
        new, ok = QtWidgets.QInputDialog.getText(self, "Renombrar", "Título:", text=card.titulo)
        if ok and new and self.listas_controller.renombrar_tarjeta(lid, card.id, new):
            self.renderizar_columnas()

    def eliminar_tarjeta_ui(self, lid, cid):
        if QtWidgets.QMessageBox.question(self, "Confirmar", "¿Eliminar tarjeta?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            if self.listas_controller.eliminar_tarjeta(lid, cid): self.renderizar_columnas()

    def crear_nueva_lista(self):
        if not hasattr(self, "current_tablero"): return
        name, ok = QtWidgets.QInputDialog.getText(self, "Nueva Lista", "Nombre:")
        if ok and name:
            if self.listas_controller.crear_lista(name): self.renderizar_columnas()

    def crear_nueva_tarjeta(self):
        if not hasattr(self, "listas_controller"): return
        listas = self.listas_controller.obtener_listas()
        if not listas: return
        lname, ok = QtWidgets.QInputDialog.getItem(self, "Nueva Tarjeta", "Lista:", [l.titulo for l in listas], 0, False)
        if not ok: return
        tlist = next((l for l in listas if l.titulo == lname), None)
        title, ok = QtWidgets.QInputDialog.getText(self, "Nueva Tarjeta", "Título:")
        if ok and title:
            if self.listas_controller.agregar_tarjeta(tlist.id, title):
                self.renderizar_columnas()

    def volver_a_tableros(self):
        self.pestanasPrincipal.setCurrentIndex(0)
        self.cargar_tableros()

    def borrar_tablero_seleccionado(self):
        row = self.listaTableros.currentRow()
        if row < 0: return
        if QtWidgets.QMessageBox.question(self, "Confirmar", "¿Borrar tablero?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            if self.db_controller.eliminar_tablero(self.tableros[row].id): self.cargar_tableros()
            
    def abrir_papelera_tableros(self):
        dialog = PapeleraTablerosDialog(self.db_controller, self)
        dialog.exec_()

    def guardar_tablero(self):
        pass

    def buscar_tarjetas(self, txt):
        if not txt:
            self.renderizar_columnas()
            return
        self.renderizar_columnas() # Reset simple filtering visuals (implementar filtro visual real si se desea)

    def cerrar_sesion(self):
        if QtWidgets.QMessageBox.question(self, "Salir", "¿Cerrar sesión?", QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            self.sesion_cerrada.emit()
            self.pestanasPrincipal.setCurrentIndex(0)

    def alternar_autoguardado(self, state):
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    from login import LoginWindow
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())