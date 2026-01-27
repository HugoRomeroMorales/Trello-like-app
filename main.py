import sys
import os
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from Controladores.Modelos import Tablero, User
from Controladores.Listas import ListasController
from Controladores.Controller_BD import SupabaseController

current_dir = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(current_dir, "Pantallas", "App.ui")

class TarjetaDetalleDialog(QtWidgets.QDialog):
    def __init__(self, tarjeta, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detalles de la Tarjeta")
        self.setMinimumSize(400, 300)
        
        # Layout principal
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(15)

        # 1. Título
        lbl_titulo = QtWidgets.QLabel("Título:")
        lbl_titulo.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(lbl_titulo)

        self.txt_titulo = QtWidgets.QLineEdit(tarjeta.titulo)
        layout.addWidget(self.txt_titulo)

        # 2. Descripción
        lbl_desc = QtWidgets.QLabel("Descripción:")
        lbl_desc.setStyleSheet("font-weight: bold; color: #555;")
        layout.addWidget(lbl_desc)

        self.txt_descripcion = QtWidgets.QPlainTextEdit(tarjeta.descripcion)
        self.txt_descripcion.setPlaceholderText("Añade una descripción más detallada...")
        layout.addWidget(self.txt_descripcion)

        # 3. Botones (Guardar / Cancelar)
        btn_layout = QtWidgets.QHBoxLayout()
        spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        btn_layout.addItem(spacer)

        self.btn_cancelar = QtWidgets.QPushButton("Cancelar")
        self.btn_guardar = QtWidgets.QPushButton("Guardar Cambios")
        
        # Estilos específicos para que se vean bien dentro del Dialog
        self.btn_guardar.setStyleSheet("background-color: #FA8072; color: white; padding: 8px 15px; border-radius: 4px; font-weight: bold;")
        self.btn_cancelar.setStyleSheet("background-color: #ddd; color: #333; padding: 8px 15px; border-radius: 4px;")

        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_guardar)
        layout.addLayout(btn_layout)

        # Conexiones
        self.btn_guardar.clicked.connect(self.accept)
        self.btn_cancelar.clicked.connect(self.reject)

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

        # Importante: no metas un setStyleSheet aquí.
        # Si lo haces, ese stylesheet local puede pisar tu QSS global.
        # La transparencia la controlamos por objectName en el QSS.


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
        self.btnNuevoTablero.clicked.connect(self.crear_tablero)
        self.btnAbrirTablero.clicked.connect(self.abrir_tablero_seleccionado)
        self.btnBorrarTablero.clicked.connect(self.borrar_tablero_seleccionado)
        self.btnCerrarSesion.clicked.connect(self.cerrar_sesion)
        self.listaTableros.itemDoubleClicked.connect(self.abrir_tablero_seleccionado)

        if hasattr(self, "comboTema"):
            self.comboTema.clear()
            self.comboTema.addItems(["Modo Oscuro", "Modo Claro", "Brutalista Salmón"])
            self.comboTema.currentIndexChanged.connect(self.al_cambiar_tema)

            if self.tema_actual == "oscuro":
                self.comboTema.setCurrentIndex(0)
            elif self.tema_actual == "claro":
                self.comboTema.setCurrentIndex(1)
            else:
                self.comboTema.setCurrentIndex(2)

        if hasattr(self, "chkAutoGuardado"):
            self.chkAutoGuardado.stateChanged.connect(self.alternar_autoguardado)

        self.btnVolverATableros.clicked.connect(self.volver_a_tableros)
        self.btnNuevaColumna.clicked.connect(self.crear_nueva_lista)
        self.btnNuevaTarjeta.clicked.connect(self.crear_nueva_tarjeta)
        self.btnGuardarTablero.clicked.connect(self.guardar_tablero)
        self.txtBuscarTarjetas.textChanged.connect(self.buscar_tarjetas)

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

        # Esto fuerza a que el estilo se vuelva a aplicar a lo que ya estaba creado
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
            try:
                new_board = self.db_controller.crear_tablero(titulo)
                if new_board:
                    QtWidgets.QMessageBox.information(self, "Éxito", f"Tablero '{titulo}' creado correctamente")
                    self.cargar_tableros()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudo crear el tablero. Verifica tu conexión a Supabase.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error al crear tablero: {e}")

    def abrir_tablero_seleccionado(self):
        current_row = self.listaTableros.currentRow()
        if current_row >= 0 and current_row < len(self.tableros):
            self.mostrar_tablero(self.tableros[current_row])

    def mostrar_tablero(self, tablero):
        self.current_tablero = tablero
        self.listas_controller = ListasController(self.current_tablero, self.db_controller)

        self.lblNombreTablero.setText(f"Tablero: {tablero.titulo}")
        self.pestanasPrincipal.setCurrentIndex(1)

        self.renderizar_columnas()

    def renderizar_columnas(self):
        while self.layoutColumnas.count():
            item = self.layoutColumnas.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        listas = self.listas_controller.obtener_listas()
        for lista in listas:
            self.agregar_columna_ui(lista)

        spacer = QtWidgets.QSpacerItem(
            20, 20,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.layoutColumnas.addItem(spacer)

    def agregar_columna_ui(self, lista):
        frame = QtWidgets.QFrame()
        frame.setMinimumWidth(340)
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setObjectName("columnaFrame")

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        header_layout = QtWidgets.QHBoxLayout()

        lbl = QtWidgets.QLabel(lista.titulo)
        lbl.setObjectName("lblColumnaHeader")
        header_layout.addWidget(lbl)

        btn_edit_list = QtWidgets.QPushButton("✎")
        btn_edit_list.setFixedSize(40, 40)
        btn_edit_list.setCursor(QtCore.Qt.PointingHandCursor)
        btn_edit_list.setToolTip("Renombrar Lista")
        btn_edit_list.setObjectName("btnColumnaHeader")
        btn_edit_list.clicked.connect(lambda _, l=lista: self.renombrar_lista_ui(l))
        header_layout.addWidget(btn_edit_list)

        btn_delete_list = QtWidgets.QPushButton("🗑")
        btn_delete_list.setFixedSize(40, 40)
        btn_delete_list.setCursor(QtCore.Qt.PointingHandCursor)
        btn_delete_list.setToolTip("Eliminar Lista")
        btn_delete_list.setObjectName("btnColumnaHeader")
        btn_delete_list.clicked.connect(lambda _, l=lista: self.eliminar_lista_ui(l))
        header_layout.addWidget(btn_delete_list)

        layout.addLayout(header_layout)

        list_widget = ListaDragDrop(lista.id)
        list_widget.setSpacing(10)
        list_widget.setObjectName("listaTarjetas")
        list_widget.cardMoved.connect(self.procesar_movimiento_tarjeta)

        # Para que la columna se vea aunque esté vacía (hueco “azul” siempre visible)
        list_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        list_widget.setMinimumHeight(220)
        list_widget.setUniformItemSizes(False)
        
        list_widget = ListaDragDrop(lista.id)
        list_widget.setSpacing(10)
        list_widget.setObjectName("listaTarjetas")
        list_widget.cardMoved.connect(self.procesar_movimiento_tarjeta)

        list_widget.itemDoubleClicked.connect(self.abrir_detalles_tarjeta)

        for card in lista.cards:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.UserRole, card.id)

            # Truco: item sin texto, sin icono (siempre vacío)
            item.setText("")
            item.setIcon(QtGui.QIcon())

            card_widget = QtWidgets.QFrame()
            card_widget.setObjectName("cardBody")
            card_widget.setMinimumHeight(80)

            card_layout = QtWidgets.QHBoxLayout(card_widget)
            card_layout.setContentsMargins(15, 10, 15, 10)
            card_layout.setSpacing(10)

            lbl_card = QtWidgets.QLabel(str(card.titulo))
            lbl_card.setWordWrap(True)
            lbl_card.setObjectName("lblCardTitle")
            card_layout.addWidget(lbl_card, 1)

            btn_edit_card = QtWidgets.QPushButton("✎")
            btn_edit_card.setFixedSize(40, 40)
            btn_edit_card.setCursor(QtCore.Qt.PointingHandCursor)
            btn_edit_card.setObjectName("btnCardAction")
            btn_edit_card.clicked.connect(lambda _, l_id=lista.id, c=card: self.renombrar_tarjeta_ui(l_id, c))
            card_layout.addWidget(btn_edit_card)

            btn_delete_card = QtWidgets.QPushButton("🗑")
            btn_delete_card.setFixedSize(40, 40)
            btn_delete_card.setCursor(QtCore.Qt.PointingHandCursor)
            btn_delete_card.setObjectName("btnCardAction")
            btn_delete_card.clicked.connect(lambda _, l_id=lista.id, c_id=card.id: self.eliminar_tarjeta_ui(l_id, c_id))
            card_layout.addWidget(btn_delete_card)

            # El alto lo marca tu widget (para que el item se adapte)
            item.setSizeHint(card_widget.sizeHint())

            list_widget.addItem(item)
            list_widget.setItemWidget(item, card_widget)

        layout.addWidget(list_widget)
        self.layoutColumnas.addWidget(frame)

    def procesar_movimiento_tarjeta(self, source_list_id, dest_list_id, card_id):
        print(f"Moviendo tarjeta {card_id} de {source_list_id} a {dest_list_id}")

        try:
            exito = self.listas_controller.mover_tarjeta(source_list_id, dest_list_id, card_id)
            self.renderizar_columnas()

            if not exito:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo mover la tarjeta en la base de datos")
        except Exception as e:
            print(f"Error al mover tarjeta: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Fallo crítico al mover: {e}")

    def renombrar_lista_ui(self, lista):
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Renombrar Lista", "Nuevo nombre:", text=lista.titulo)
        if ok and new_name:
            try:
                if self.listas_controller.renombrar_lista(lista.id, new_name):
                    self.renderizar_columnas()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudo renombrar la lista")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error al renombrar lista: {str(e)}")

    def eliminar_lista_ui(self, lista):
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar lista '{lista.titulo}'?\n\nEsto eliminará todas las tarjetas de la lista.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                if self.listas_controller.eliminar_lista(lista.id):
                    self.renderizar_columnas()
                    QtWidgets.QMessageBox.information(self, "Éxito", f"Lista '{lista.titulo}' eliminada")
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudo eliminar la lista")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error al eliminar lista: {str(e)}")

    def renombrar_tarjeta_ui(self, list_id, card):
        new_name, ok = QtWidgets.QInputDialog.getText(self, "Renombrar Tarjeta", "Nuevo título:", text=card.titulo)
        if ok and new_name:
            try:
                if self.listas_controller.renombrar_tarjeta(list_id, card.id, new_name):
                    self.renderizar_columnas()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudo renombrar la tarjeta")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error al renombrar tarjeta: {str(e)}")

    def eliminar_tarjeta_ui(self, list_id, card_id):
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar tarjeta?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                if self.listas_controller.eliminar_tarjeta(list_id, card_id):
                    self.renderizar_columnas()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudo eliminar la tarjeta")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error al eliminar tarjeta: {str(e)}")

    def abrir_detalles_tarjeta(self, item):
        card_id = item.data(QtCore.Qt.UserRole)
        list_widget = self.sender()
        list_id = list_widget.list_id 

        lista_obj = next((l for l in self.listas_controller.obtener_listas() if l.id == list_id), None)
        if not lista_obj: return

        tarjeta_obj = next((c for c in lista_obj.cards if c.id == card_id), None)
        if not tarjeta_obj: return


        dialog = TarjetaDetalleDialog(tarjeta_obj, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_title, new_desc = dialog.get_data()
            
            if new_title != tarjeta_obj.titulo or new_desc != tarjeta_obj.descripcion:
                if self.listas_controller.actualizar_contenido_tarjeta(list_id, card_id, new_title, new_desc):
                    self.renderizar_columnas() 
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudieron guardar los cambios")

    def crear_nueva_lista(self):
        if not hasattr(self, "current_tablero"):
            QtWidgets.QMessageBox.warning(self, "Error", "No hay un tablero abierto")
            return

        titulo, ok = QtWidgets.QInputDialog.getText(self, "Nueva Lista", "Nombre de la lista:")
        if ok and titulo:
            try:
                nueva_lista = self.listas_controller.crear_lista(titulo)
                if nueva_lista:
                    self.renderizar_columnas()
                    QtWidgets.QMessageBox.information(self, "Éxito", f"Lista '{titulo}' creada correctamente")
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudo crear la lista")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error al crear lista: {str(e)}")
                print(f"Error detallado al crear lista: {e}")

    def crear_nueva_tarjeta(self):
        if not hasattr(self, "listas_controller"):
            QtWidgets.QMessageBox.warning(self, "Error", "No hay un tablero abierto")
            return

        try:
            listas = self.listas_controller.obtener_listas()

            if not listas:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Error",
                    "No hay listas en este tablero.\n\nCrea una lista primero usando 'Nueva columna'."
                )
                return

            list_names = [l.titulo for l in listas]
            list_name, ok = QtWidgets.QInputDialog.getItem(
                self,
                "Nueva Tarjeta",
                "Seleccionar lista:",
                list_names,
                0,
                False
            )

            if not ok or not list_name:
                return

            target_list = next((l for l in listas if l.titulo == list_name), None)
            if not target_list:
                QtWidgets.QMessageBox.warning(self, "Error", "No se encontró la lista seleccionada")
                return

            titulo, ok = QtWidgets.QInputDialog.getText(self, "Nueva Tarjeta", "Título de la tarjeta:")
            if not ok or not titulo:
                return

            nueva_tarjeta = self.listas_controller.agregar_tarjeta(target_list.id, titulo)

            if nueva_tarjeta:
                self.renderizar_columnas()
                QtWidgets.QMessageBox.information(self, "Éxito", f"Tarjeta '{titulo}' creada en '{list_name}'")
            else:
                QtWidgets.QMessageBox.warning(self, "Error", "No se pudo crear la tarjeta. Verifica tu conexión a Supabase.")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error al crear tarjeta: {str(e)}")
            print(f"Error detallado al crear tarjeta: {e}")
            import traceback
            traceback.print_exc()

    def volver_a_tableros(self):
        self.pestanasPrincipal.setCurrentIndex(0)
        self.cargar_tableros()

    def borrar_tablero_seleccionado(self):
        current_row = self.listaTableros.currentRow()

        if not getattr(self, "tableros", None):
            QtWidgets.QMessageBox.warning(self, "Advertencia", "No hay tableros para eliminar")
            return

        if current_row < 0:
            QtWidgets.QMessageBox.warning(self, "Advertencia", "Por favor, selecciona un tablero para eliminar")
            return

        if current_row >= len(self.tableros):
            QtWidgets.QMessageBox.warning(self, "Error", "Tablero inválido seleccionado")
            return

        tablero = self.tableros[current_row]
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar el tablero '{tablero.titulo}'?\n\nEsta acción no se puede deshacer y eliminará todas las listas y tarjetas del tablero.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                if self.db_controller.eliminar_tablero(tablero.id):
                    QtWidgets.QMessageBox.information(self, "Éxito", f"Tablero '{tablero.titulo}' eliminado correctamente")
                    self.cargar_tableros()
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", "No se pudo eliminar el tablero. Verifica tu conexión.")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Error al eliminar tablero: {e}")

    def guardar_tablero(self):
        if not hasattr(self, "current_tablero"):
            return
        QtWidgets.QMessageBox.information(self, "Guardado", "Los cambios se guardan automáticamente")

    def buscar_tarjetas(self, texto):
        if not hasattr(self, "listas_controller"):
            return

        if not texto:
            self.renderizar_columnas()
            return

        texto_lower = texto.lower()

        while self.layoutColumnas.count():
            item = self.layoutColumnas.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        listas = self.listas_controller.obtener_listas()

        for lista in listas:
            tarjetas_filtradas = [card for card in lista.cards if texto_lower in card.titulo.lower()]
            if tarjetas_filtradas:
                lista_filtrada = type("obj", (object,), {
                    "id": lista.id,
                    "titulo": lista.titulo,
                    "cards": tarjetas_filtradas
                })
                self.agregar_columna_ui(lista_filtrada)

        spacer = QtWidgets.QSpacerItem(
            20, 20,
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.layoutColumnas.addItem(spacer)

    def cerrar_sesion(self):
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Cerrar Sesión",
            "¿Estás seguro de que quieres cerrar sesión?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            self.sesion_cerrada.emit()
            if hasattr(self, "current_tablero"):
                delattr(self, "current_tablero")
            self.pestanasPrincipal.setCurrentIndex(0)

    def alternar_autoguardado(self, estado):
        if estado == QtCore.Qt.Checked:
            QtWidgets.QMessageBox.information(self, "Autoguardado", "Autoguardado activado")
        else:
            QtWidgets.QMessageBox.information(self, "Autoguardado", "Autoguardado desactivado")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    from login import LoginWindow
    window = LoginWindow()
    window.show()

    sys.exit(app.exec_())
