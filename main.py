import sys
import os
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QSettings
from Controladores.Modelos import Tablero, User
from Controladores.Listas import ListasController
from Controladores.Controller_BD import SupabaseController

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "Pantallas", "App.ui")


def icono_svg(nombre_archivo: str) -> QtGui.QIcon:
    return QtGui.QIcon(os.path.join(current_dir, "assets", "icons", nombre_archivo))


# --- DIÁLOGO DE DETALLES Y ASIGNACIÓN ---
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

        group_info = QtWidgets.QGroupBox("Información")
        form_layout = QtWidgets.QFormLayout(group_info)

        self.txt_titulo = QtWidgets.QLineEdit(tarjeta.titulo)
        form_layout.addRow("Título:", self.txt_titulo)

        self.txt_descripcion = QtWidgets.QPlainTextEdit(tarjeta.descripcion)
        self.txt_descripcion.setPlaceholderText("Añade una descripción...")
        self.txt_descripcion.setMinimumHeight(100)
        form_layout.addRow("Descripción:", self.txt_descripcion)

        main_layout.addWidget(group_info)

        group_assign = QtWidgets.QGroupBox("Usuarios Asignados")
        assign_layout = QtWidgets.QVBoxLayout(group_assign)

        add_layout = QtWidgets.QHBoxLayout()
        self.combo_users = QtWidgets.QComboBox()
        users = self.controller.obtener_todos_usuarios()
        for u in users:
            self.combo_users.addItem(u.username, u.id)

        btn_asignar = QtWidgets.QPushButton("Asignar")
        btn_asignar.clicked.connect(self.asignar_usuario)
        btn_asignar.setStyleSheet(
            "background-color: #e0e0e0; color: black; border-radius: 4px; padding: 5px;"
        )

        add_layout.addWidget(self.combo_users)
        add_layout.addWidget(btn_asignar)
        assign_layout.addLayout(add_layout)

        self.list_assigned = QtWidgets.QListWidget()
        self.list_assigned.setFixedHeight(80)
        assign_layout.addWidget(self.list_assigned)

        btn_quitar = QtWidgets.QPushButton("Quitar Seleccionado")
        btn_quitar.clicked.connect(self.quitar_usuario)
        btn_quitar.setStyleSheet("color: red; border: 1px solid #ffcccc; border-radius: 4px;")
        assign_layout.addWidget(btn_quitar)

        main_layout.addWidget(group_assign)

        self.refrescar_lista_asignados()

        btn_layout = QtWidgets.QHBoxLayout()
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QtWidgets.QPushButton("Guardar Cambios")
        self.btn_guardar.setStyleSheet(
            "background-color: #FA8072; color: white; font-weight: bold; padding: 8px; border-radius: 4px;"
        )
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
        if not uid or any(u.id == uid for u in self.tarjeta.assignees):
            return
        if self.controller.gestionar_asignacion(self.list_id, self.tarjeta.id, uid, True):
            self.refrescar_lista_asignados()

    def quitar_usuario(self):
        row = self.list_assigned.currentRow()
        if row < 0:
            return
        user = self.tarjeta.assignees[row]
        if self.controller.gestionar_asignacion(self.list_id, self.tarjeta.id, user.id, False):
            self.refrescar_lista_asignados()

    def get_data(self):
        return self.txt_titulo.text(), self.txt_descripcion.toPlainText()


# --- LISTA DRAG & DROP ---
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


def confirmar_accion(parent, titulo, texto, texto_si="Sí", texto_no="No"):
    msg = QtWidgets.QMessageBox(parent)
    msg.setIcon(QtWidgets.QMessageBox.Question)
    msg.setWindowTitle(titulo)
    msg.setText(texto)

    msg.setStyleSheet(
        """
        QMessageBox { background: #ffffff; }
        QLabel { color: #0d1b2a; font-size: 14px; }
        QPushButton {
            background: #FA8072;
            color: white;
            border: 1px solid #FA8072;
            border-radius: 6px;
            padding: 6px 14px;
            min-width: 120px;
            min-height: 34px;
            font-weight: 600;
        }
        QPushButton:hover { background: #FF6347; }
        """
    )

    btn_si = msg.addButton(texto_si, QtWidgets.QMessageBox.YesRole)
    btn_no = msg.addButton(texto_no, QtWidgets.QMessageBox.NoRole)
    msg.setDefaultButton(btn_no)

    msg.exec()
    return msg.clickedButton() == btn_si


# --- PAPELERA DE TABLEROS ---
class PapeleraTablerosDialog(QtWidgets.QDialog):
    def __init__(self, db_controller, parent=None):
        super().__init__(parent)
        self.db = db_controller
        self.setWindowTitle("Papelera de Tableros")
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: white;")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Tableros Eliminados"))

        self.lista = QtWidgets.QListWidget()
        layout.addWidget(self.lista)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_restaurar = QtWidgets.QPushButton("♻ Restaurar")
        btn_restaurar.setStyleSheet("background-color: #4CAF50; color: white; padding: 6px;")
        btn_restaurar.clicked.connect(self.restaurar)

        btn_borrar = QtWidgets.QPushButton("🔥 Borrar Definitivamente")
        btn_borrar.setStyleSheet("background-color: #f44336; color: white; padding: 6px;")
        btn_borrar.clicked.connect(self.borrar_final)

        btn_layout.addWidget(btn_restaurar)
        btn_layout.addWidget(btn_borrar)
        layout.addLayout(btn_layout)

        self.cargar()

    def cargar(self):
        self.lista.clear()
        self.tableros = self.db.obtener_papelera_tableros()
        if not self.tableros:
            self.lista.addItem("Papelera vacía")
            return
        for t in self.tableros:
            item = QtWidgets.QListWidgetItem(f"📁 {t.titulo}")
            item.setData(QtCore.Qt.UserRole, t.id)
            self.lista.addItem(item)

    def restaurar(self):
        row = self.lista.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona un tablero primero")
            return

        if confirmar_accion(self, "Confirmar Restauración", "¿Seguro que quieres restaurar este tablero?", "Sí, restaurar"):
            tid = self.lista.currentItem().data(QtCore.Qt.UserRole)
            if self.db.restaurar_tablero(tid):
                self.cargar()
                self.parent().cargar_tableros()
                QtWidgets.QMessageBox.information(self, "Listo", "Tablero restaurado")

    def borrar_final(self):
        row = self.lista.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona un tablero primero")
            return

        if confirmar_accion(self, "PELIGRO", "¿Borrar para siempre? SE PERDERÁ TODO EL CONTENIDO.\nNo se puede deshacer.", "Sí, borrar", "Cancelar"):
            tid = self.lista.currentItem().data(QtCore.Qt.UserRole)
            if self.db.eliminar_tablero_definitivamente(tid):
                self.cargar()


# --- PAPELERA DE COLUMNAS (LISTAS) ---
class PapeleraListasDialog(QtWidgets.QDialog):
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

        self.lista_papelera = QtWidgets.QListWidget()
        self.lista_papelera.setStyleSheet(
            """
            QListWidget { border: 1px solid #ccc; border-radius: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #eee; }
            """
        )
        layout.addWidget(self.lista_papelera)

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
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona una columna primero")
            return

        if confirmar_accion(self, "Restaurar", "¿Quieres devolver esta columna al tablero?", "Sí, restaurar"):
            item = self.lista_papelera.currentItem()
            list_id = item.data(QtCore.Qt.UserRole)

            if self.controller.restaurar_lista_papelera(list_id):
                QtWidgets.QMessageBox.information(self, "Éxito", "Columna restaurada")
                self.cargar_datos()
                if self.parent():
                    self.parent().renderizar_columnas()

    def borrar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona una columna primero")
            return

        if confirmar_accion(self, "ELIMINAR DEFINITIVAMENTE", "⚠ ¿Borrar para siempre? Se perderán todas sus tarjetas.\nNo se puede deshacer.", "Sí, borrar", "Cancelar"):
            item = self.lista_papelera.currentItem()
            list_id = item.data(QtCore.Qt.UserRole)

            if self.controller.eliminar_lista_definitivamente(list_id):
                self.cargar_datos()
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo eliminar")


# --- PAPELERA DE TARJETAS ---
class PapeleraDialog(QtWidgets.QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Papelera de Tarjetas")
        self.setMinimumSize(500, 400)
        self.setStyleSheet("background-color: #ffffff;")

        layout = QtWidgets.QVBoxLayout(self)

        lbl = QtWidgets.QLabel("Tarjetas Eliminadas")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(lbl)

        self.lista_papelera = QtWidgets.QListWidget()
        self.lista_papelera.setStyleSheet(
            """
            QListWidget { border: 1px solid #ccc; border-radius: 5px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #eee; }
            """
        )
        layout.addWidget(self.lista_papelera)

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
        self.items_data = self.controller.obtener_papelera()

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
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona una tarjeta primero")
            return

        if confirmar_accion(self, "Restaurar", "¿Quieres devolver esta tarjeta al tablero?", "Sí, restaurar"):
            item = self.lista_papelera.currentItem()
            card_id = item.data(QtCore.Qt.UserRole)

            if self.controller.restaurar_tarjeta(card_id):
                QtWidgets.QMessageBox.information(self, "Éxito", "Tarjeta restaurada")
                self.cargar_datos()
                if self.parent():
                    self.parent().renderizar_columnas()

    def borrar_seleccionada(self):
        row = self.lista_papelera.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona una tarjeta primero")
            return

        if confirmar_accion(self, "ELIMINAR PARA SIEMPRE", "⚠ ¿Borrar definitivamente? Esta acción es IRREVERSIBLE.", "Sí, borrar", "Cancelar"):
            item = self.lista_papelera.currentItem()
            card_id = item.data(QtCore.Qt.UserRole)

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

        self.settings = QSettings("MiniTrello", "App")

        self.tema_actual = "brutalista"
        self.cargar_tema(self.tema_actual)
        self.db_controller = SupabaseController()
        self.current_user = User(username="UsuarioDemo")

        self.filtro_usuario = None
        self.filtro_columna = None

        self.tamano_fuente = self.settings.value("tamano_fuente", 14, type=int)

        self.pestanasPrincipal.setUsesScrollButtons(True)
        self.pestanasPrincipal.setElideMode(QtCore.Qt.ElideNone)
        self.pestanasPrincipal.tabBar().setExpanding(False)

        self.configurar_conexiones()
        self.pestanasPrincipal.setCurrentIndex(0)
        self.cargar_tableros()

        self.aplicar_tamano_fuente(self.tamano_fuente)

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
        self.txtBuscarTarjetas.textChanged.connect(self.buscar_tarjetas)

        if hasattr(self, "comboTema"):
            self.comboTema.clear()
            self.comboTema.addItems(["Modo Oscuro", "Modo Claro", "Brutalista Salmón"])
            self.comboTema.currentIndexChanged.connect(self.al_cambiar_tema)
            self.comboTema.setCurrentIndex(0 if self.tema_actual == "oscuro" else 1 if self.tema_actual == "claro" else 2)

        if hasattr(self, "chkAutoGuardado"):
            self.chkAutoGuardado.stateChanged.connect(self.alternar_autoguardado)

        if hasattr(self, "layoutAjustes"):
            self._crear_controles_fuente()

        if not hasattr(self, 'btnPapeleraTableros'):
            parent_layout = self.btnNuevoTablero.parentWidget().layout()

            self.btnPapeleraTableros = QtWidgets.QPushButton("Papelera Tableros")
            self.btnPapeleraTableros.setCursor(QtCore.Qt.PointingHandCursor)
            self.btnPapeleraTableros.setIcon(icono_svg("trash.svg"))
            self.btnPapeleraTableros.setIconSize(QtCore.QSize(18, 18))
            self.btnPapeleraTableros.setStyleSheet("background-color: #ECEFF1; color: #455A64; border: 1px solid #CFD8DC; padding: 6px; font-weight: bold;")
            self.btnPapeleraTableros.clicked.connect(self.abrir_papelera_tableros)
            parent_layout.addWidget(self.btnPapeleraTableros)

        self.btnVolverATableros.clicked.connect(self.volver_a_tableros)
        self.btnNuevaColumna.clicked.connect(self.crear_nueva_lista)
        self.btnNuevaTarjeta.clicked.connect(self.crear_nueva_tarjeta)
        self.btnGuardarTablero.clicked.connect(self.guardar_tablero)
        self.txtBuscarTarjetas.textChanged.connect(self.buscar_tarjetas)

        self._crear_controles_filtros()

    def _crear_controles_fuente(self):
        fuente_container = QtWidgets.QWidget()
        fuente_layout = QtWidgets.QHBoxLayout(fuente_container)
        fuente_layout.setContentsMargins(0, 10, 0, 10)

        lbl_fuente = QtWidgets.QLabel("Tamaño de fuente:")
        fuente_layout.addWidget(lbl_fuente)

        btn_menos = QtWidgets.QPushButton("−")
        btn_menos.setFixedSize(30, 30)
        btn_menos.clicked.connect(lambda: self._cambiar_fuente(-1))
        fuente_layout.addWidget(btn_menos)

        self.sliderFuente = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sliderFuente.setMinimum(10)
        self.sliderFuente.setMaximum(24)
        self.sliderFuente.setValue(self.tamano_fuente)
        self.sliderFuente.setFixedWidth(150)
        self.sliderFuente.valueChanged.connect(self.aplicar_tamano_fuente)
        fuente_layout.addWidget(self.sliderFuente)

        btn_mas = QtWidgets.QPushButton("+")
        btn_mas.setFixedSize(30, 30)
        btn_mas.clicked.connect(lambda: self._cambiar_fuente(1))
        fuente_layout.addWidget(btn_mas)

        self.lblFuenteValor = QtWidgets.QLabel(f"{self.tamano_fuente}px")
        self.lblFuenteValor.setFixedWidth(45)
        fuente_layout.addWidget(self.lblFuenteValor)

        fuente_layout.addStretch()
        self.layoutAjustes.insertWidget(3, fuente_container)

    def _cambiar_fuente(self, delta):
        nuevo = self.sliderFuente.value() + delta
        nuevo = max(10, min(24, nuevo))
        self.sliderFuente.setValue(nuevo)

    def aplicar_tamano_fuente(self, size):
        self.tamano_fuente = size
        self.settings.setValue("tamano_fuente", size)

        if hasattr(self, 'lblFuenteValor'):
            self.lblFuenteValor.setText(f"{size}px")

        current_style = self.styleSheet()
        font_style = f"\n* {{ font-size: {size}px; }}"

        import re
        if re.search(r'\*\s*\{[^}]*font-size:', current_style):
            current_style = re.sub(r'(\*\s*\{[^}]*font-size:)\s*\d+px', f'\\1 {size}px', current_style)
            self.setStyleSheet(current_style)
        else:
            self.setStyleSheet(current_style + font_style)

    def _crear_controles_filtros(self):
        parent_layout = self.txtBuscarTarjetas.parentWidget().layout()

        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.VLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.comboFiltroUsuario = QtWidgets.QComboBox()
        self.comboFiltroUsuario.setMinimumWidth(120)
        self.comboFiltroUsuario.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.comboFiltroUsuario.addItem("👤 Todos los usuarios", None)
        self.comboFiltroUsuario.currentIndexChanged.connect(self._aplicar_filtro_usuario)

        self.comboFiltroColumna = QtWidgets.QComboBox()
        self.comboFiltroColumna.setMinimumWidth(120)
        self.comboFiltroColumna.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.comboFiltroColumna.addItem("📋 Todas las columnas", None)
        self.comboFiltroColumna.currentIndexChanged.connect(self._aplicar_filtro_columna)

        self.btnLimpiarFiltros = QtWidgets.QPushButton("✕ Limpiar")
        self.btnLimpiarFiltros.setMinimumWidth(100)
        self.btnLimpiarFiltros.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.btnLimpiarFiltros.clicked.connect(self._limpiar_filtros)

        idx = parent_layout.indexOf(self.txtBuscarTarjetas)
        parent_layout.insertWidget(idx + 1, separator)
        parent_layout.insertWidget(idx + 2, self.comboFiltroUsuario)
        parent_layout.insertWidget(idx + 3, self.comboFiltroColumna)
        parent_layout.insertWidget(idx + 4, self.btnLimpiarFiltros)

    def _cargar_opciones_filtros(self):
        usuario_actual = self.comboFiltroUsuario.currentData()
        columna_actual = self.comboFiltroColumna.currentData()

        self.comboFiltroUsuario.blockSignals(True)
        self.comboFiltroUsuario.clear()
        self.comboFiltroUsuario.addItem("👤 Todos los usuarios", None)

        usuarios = self.db_controller.obtener_todos_usuarios()
        for u in usuarios:
            self.comboFiltroUsuario.addItem(f"👤 {u.username}", u.id)

        if usuario_actual:
            idx = self.comboFiltroUsuario.findData(usuario_actual)
            if idx >= 0:
                self.comboFiltroUsuario.setCurrentIndex(idx)
        self.comboFiltroUsuario.blockSignals(False)

        self.comboFiltroColumna.blockSignals(True)
        self.comboFiltroColumna.clear()
        self.comboFiltroColumna.addItem("📋 Todas las columnas", None)

        if hasattr(self, 'listas_controller'):
            for lista in self.listas_controller.obtener_listas():
                self.comboFiltroColumna.addItem(f"📋 {lista.titulo}", lista.id)

        if columna_actual:
            idx = self.comboFiltroColumna.findData(columna_actual)
            if idx >= 0:
                self.comboFiltroColumna.setCurrentIndex(idx)
        self.comboFiltroColumna.blockSignals(False)

    def _aplicar_filtro_usuario(self, index):
        self.filtro_usuario = self.comboFiltroUsuario.currentData()
        if hasattr(self, 'listas_controller'):
            self.renderizar_columnas()

    def _aplicar_filtro_columna(self, index):
        self.filtro_columna = self.comboFiltroColumna.currentData()
        if hasattr(self, 'listas_controller'):
            self.renderizar_columnas()

    def _limpiar_filtros(self):
        self.comboFiltroUsuario.setCurrentIndex(0)
        self.comboFiltroColumna.setCurrentIndex(0)
        self.txtBuscarTarjetas.clear()
        self.filtro_usuario = None
        self.filtro_columna = None
        if hasattr(self, 'listas_controller'):
            self.renderizar_columnas()

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
            tablero = self.db_controller.crear_tablero(titulo)
            if tablero:
                self.cargar_tableros()
                QtWidgets.QMessageBox.information(self, "Éxito", f"Tablero '{titulo}' creado correctamente")
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo crear el tablero.\n\nVerifica que la conexión a la base de datos esté correcta.")

    def abrir_tablero_seleccionado(self):
        row = self.listaTableros.currentRow()
        if 0 <= row < len(self.tableros):
            self.mostrar_tablero(self.tableros[row])

    def mostrar_tablero(self, tablero):
        self.current_tablero = tablero
        self.listas_controller = ListasController(self.current_tablero, self.db_controller)
        self.listas_controller.cargar_asignados_iniciales()

        self.lblNombreTablero.setText(f"Tablero: {tablero.titulo}")
        self.pestanasPrincipal.setCurrentIndex(1)
        self.renderizar_columnas()
        self._cargar_opciones_filtros()

        if not hasattr(self, 'btnPapelera'):
            parent_layout = self.btnVolverATableros.parentWidget().layout()

            self.btnPapelera = QtWidgets.QPushButton("Papelera Tarjetas")
            self.btnPapelera.setCursor(QtCore.Qt.PointingHandCursor)
            self.btnPapelera.setIcon(icono_svg("trash.svg"))
            self.btnPapelera.setIconSize(QtCore.QSize(18, 18))
            self.btnPapelera.setStyleSheet("background-color: #FFEBEE; color: #D32F2F; border: 1px solid #FFCDD2; padding: 5px 10px; border-radius: 4px; font-weight: bold;")
            self.btnPapelera.clicked.connect(self.abrir_papelera)

            self.btnPapeleraColumnas = QtWidgets.QPushButton("Papelera Columnas")
            self.btnPapeleraColumnas.setCursor(QtCore.Qt.PointingHandCursor)
            self.btnPapeleraColumnas.setIcon(icono_svg("trash.svg"))
            self.btnPapeleraColumnas.setIconSize(QtCore.QSize(18, 18))
            self.btnPapeleraColumnas.setStyleSheet("background-color: #E8F5E9; color: #388E3C; border: 1px solid #C8E6C9; padding: 5px 10px; border-radius: 4px; font-weight: bold;")
            self.btnPapeleraColumnas.clicked.connect(self.abrir_papelera_columnas)

            parent_layout.insertWidget(parent_layout.count() - 1, self.btnPapelera)
            parent_layout.insertWidget(parent_layout.count() - 1, self.btnPapeleraColumnas)

        self.renderizar_columnas()

    def abrir_papelera(self):
        if not hasattr(self, 'listas_controller'):
            return
        dialog = PapeleraDialog(self.listas_controller, self)
        dialog.exec_()

    def abrir_papelera_columnas(self):
        if not hasattr(self, 'listas_controller'):
            return
        dialog = PapeleraListasDialog(self.listas_controller, self)
        dialog.exec_()

    def renderizar_columnas(self):
        while self.layoutColumnas.count():
            item = self.layoutColumnas.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        for lista in self.listas_controller.obtener_listas():
            if self.filtro_columna and lista.id != self.filtro_columna:
                continue
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

        header = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(lista.titulo)
        lbl.setObjectName("lblColumnaHeader")
        header.addWidget(lbl)

        btn_edit = QtWidgets.QPushButton()
        btn_edit.setFixedSize(40, 40)
        btn_edit.setCursor(QtCore.Qt.PointingHandCursor)
        btn_edit.setObjectName("btnColumnaHeader")
        btn_edit.setIcon(icono_svg("edit.svg"))
        btn_edit.setIconSize(QtCore.QSize(18, 18))
        btn_edit.clicked.connect(lambda _, l=lista: self.renombrar_lista_ui(l))
        header.addWidget(btn_edit)

        btn_del = QtWidgets.QPushButton()
        btn_del.setFixedSize(40, 40)
        btn_del.setCursor(QtCore.Qt.PointingHandCursor)
        btn_del.setObjectName("btnColumnaHeader")
        btn_del.setIcon(icono_svg("trash.svg"))
        btn_del.setIconSize(QtCore.QSize(18, 18))
        btn_del.clicked.connect(lambda _, l=lista: self.eliminar_lista_ui(l))
        header.addWidget(btn_del)

        layout.addLayout(header)

        list_widget = ListaDragDrop(lista.id)
        list_widget.setSpacing(10)
        list_widget.setObjectName("listaTarjetas")
        list_widget.cardMoved.connect(self.procesar_movimiento_tarjeta)
        list_widget.itemDoubleClicked.connect(self.abrir_detalles_tarjeta)

        list_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        list_widget.setMinimumHeight(200)
        list_widget.setUniformItemSizes(False)

        for card in lista.cards:
            if self.filtro_usuario:
                asignado_ids = [u.id for u in card.assignees]
                if self.filtro_usuario not in asignado_ids:
                    continue

            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, card.id)
            item.setText("")

            card_widget = QtWidgets.QFrame()
            card_widget.setObjectName("cardBody")
            card_widget.setMinimumHeight(80)

            card_layout = QtWidgets.QHBoxLayout(card_widget)
            card_layout.setContentsMargins(15, 10, 15, 10)

            lbl_card = QtWidgets.QLabel(str(card.titulo))
            lbl_card.setWordWrap(True)
            lbl_card.setObjectName("lblCardTitle")
            card_layout.addWidget(lbl_card, 1)

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

            btn_edit_c = QtWidgets.QPushButton()
            btn_edit_c.setFixedSize(40, 40)
            btn_edit_c.setCursor(QtCore.Qt.PointingHandCursor)
            btn_edit_c.setObjectName("btnCardAction")
            btn_edit_c.setIcon(icono_svg("edit.svg"))
            btn_edit_c.setIconSize(QtCore.QSize(16, 16))
            btn_edit_c.clicked.connect(lambda _, l_id=lista.id, c=card: self.renombrar_tarjeta_ui(l_id, c))
            card_layout.addWidget(btn_edit_c)

            btn_del_c = QtWidgets.QPushButton()
            btn_del_c.setFixedSize(40, 40)
            btn_del_c.setCursor(QtCore.Qt.PointingHandCursor)
            btn_del_c.setObjectName("btnCardAction")
            btn_del_c.setIcon(icono_svg("trash.svg"))
            btn_del_c.setIconSize(QtCore.QSize(16, 16))
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
        if not lista_obj:
            return
        tarjeta_obj = next((c for c in lista_obj.cards if c.id == card_id), None)
        if not tarjeta_obj:
            return

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
        if confirmar_accion(self, "Eliminar", f"¿Eliminar lista '{lista.titulo}'?", "Sí, eliminar"):
            if self.listas_controller.eliminar_lista(lista.id):
                self.renderizar_columnas()

    def renombrar_tarjeta_ui(self, lid, card):
        new, ok = QtWidgets.QInputDialog.getText(self, "Renombrar", "Título:", text=card.titulo)
        if ok and new and self.listas_controller.renombrar_tarjeta(lid, card.id, new):
            self.renderizar_columnas()

    def eliminar_tarjeta_ui(self, lid, cid):
        if confirmar_accion(self, "Eliminar", "¿Eliminar tarjeta?", "Sí, eliminar"):
            if self.listas_controller.eliminar_tarjeta(lid, cid):
                self.renderizar_columnas()

    def crear_nueva_lista(self):
        if not hasattr(self, "current_tablero"):
            return
        name, ok = QtWidgets.QInputDialog.getText(self, "Nueva Lista", "Nombre:")
        if ok and name:
            lista = self.listas_controller.crear_lista(name)
            if lista:
                self.renderizar_columnas()
                QtWidgets.QMessageBox.information(self, "Éxito", f"Columna '{name}' creada correctamente")
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo crear la columna.\n\nVerifica la conexión a la base de datos.")

    def crear_nueva_tarjeta(self):
        if not hasattr(self, "listas_controller"):
            return
        listas = self.listas_controller.obtener_listas()
        if not listas:
            return
        lname, ok = QtWidgets.QInputDialog.getItem(self, "Nueva Tarjeta", "Lista:", [l.titulo for l in listas], 0, False)
        if not ok:
            return
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
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecciona un tablero primero")
            return

        if confirmar_accion(self, "Borrar Tablero", "¿Borrar este tablero?", "Sí, borrar"):
            if self.db_controller.eliminar_tablero(self.tableros[row].id):
                self.cargar_tableros()

    def abrir_papelera_tableros(self):
        dialog = PapeleraTablerosDialog(self.db_controller, self)
        dialog.exec_()

    def guardar_tablero(self):
        pass

    def buscar_tarjetas(self, txt):
        if not txt:
            self.renderizar_columnas()
            return
        self.renderizar_columnas()

    def cerrar_sesion(self):
        if confirmar_accion(self, "Salir", "¿Cerrar sesión?", "Sí, cerrar"):
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
