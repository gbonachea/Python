# Navegador tipo Chrome en PyQt5/QtWebEngine
# Requiere: pip install PyQt5 PyQtWebEngine

import sys
import os
import json
import hashlib
import urllib.parse
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QAction, QLineEdit, QTabWidget, QWidget, QVBoxLayout,
    QToolButton, QMenu, QDialog, QLabel, QListWidget, QPushButton, QButtonGroup, QRadioButton,
    QHBoxLayout, QProgressBar, QListWidgetItem, QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QUrl, Qt, QTimer, pyqtSignal, pyqtSlot, QObject, QJsonDocument
import json
import shutil
import subprocess

class PWAHandler(QObject):
    """Manejador de PWAs"""
    manifestFound = pyqtSignal(dict)  # Señal emitida cuando se encuentra un manifest válido
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.checking = False
        
    def check_pwa_support(self):
        """Verifica si el sitio actual es una PWA"""
        if self.checking:
            return
            
        self.checking = True
        print("Verificando soporte PWA...")  # Depuración
        
        # Script mejorado para detectar PWAs
        self.page.runJavaScript('''
        (async function checkPWA() {
            try {
                // Función para verificar manifest
                async function fetchManifest(url) {
                    try {
                        const response = await fetch(url);
                        if (!response.ok) return null;
                        return await response.json();
                    } catch (e) {
                        console.log("Error fetching manifest:", e);
                        return null;
                    }
                }

                // 1. Buscar links de manifest en el DOM
                let manifest = null;
                const manifestLinks = document.querySelectorAll('link[rel="manifest"]');
                for (const link of manifestLinks) {
                    manifest = await fetchManifest(link.href);
                    if (manifest) break;
                }

                // 2. Intentar ubicaciones comunes si no se encontró
                const commonPaths = [
                    '/manifest.json',
                    '/manifest.webmanifest',
                    '/app.webmanifest',
                    '/pwa.webmanifest'
                ];

                if (!manifest) {
                    for (const path of commonPaths) {
                        manifest = await fetchManifest(new URL(path, window.location.href).href);
                        if (manifest) break;
                    }
                }

                if (!manifest) {
                    console.log("No manifest found");
                    return null;
                }

                // 3. Verificar service worker
                let hasServiceWorker = false;
                if ('serviceWorker' in navigator) {
                    const registrations = await navigator.serviceWorker.getRegistrations();
                    hasServiceWorker = registrations.length > 0;
                }

                // 4. Verificar características mínimas del manifest
                const requiredFields = ['name', 'start_url', 'display'];
                const hasRequiredFields = requiredFields.every(field => manifest[field]);
                const validDisplay = ['standalone', 'fullscreen', 'minimal-ui'].includes(manifest.display);

                if (hasRequiredFields && validDisplay) {
                    manifest.currentUrl = window.location.href;
                    manifest.hasServiceWorker = hasServiceWorker;
                    console.log("PWA válida encontrada:", manifest);
                    return manifest;
                }

                console.log("Manifest found but missing required fields or invalid display mode");
                return null;
            } catch (error) {
                console.log("Error checking PWA:", error);
                return null;
            }
        })();
        ''', self._handle_manifest_result)
    
    def _handle_manifest_result(self, result):
        """Maneja el resultado de la verificación del manifest"""
        self.checking = False
        if result:
            print("¡Manifest encontrado!", result)  # Depuración
            self.manifestFound.emit(result)

class BrowserTab(QWidget):
    pwaAvailable = pyqtSignal(dict)  # Nueva señal para indicar que hay una PWA disponible
    current_manifest = None  # Almacena el manifest de la PWA actual
    
    def __init__(self, icons_path):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.icons_path = icons_path
        
        # Crear barra de navegación
        self.navbar = QToolBar()
        self.navbar.setStyleSheet('''
            QToolBar {
                spacing: 5px;
                padding: 5px;
                background-color: var(--toolbar);
                border: none;
            }
            QToolButton {
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QToolButton:hover {
                background-color: var(--hover);
            }
        ''')
        
        # Crear el webview
        self.webview = QWebEngineView()
        
        # Botón de instalación PWA (inicialmente oculto)
        self.install_pwa_btn = QToolButton(self.navbar)
        self.install_pwa_btn.setIcon(QIcon(os.path.join(icons_path, 'extension.png')))
        self.install_pwa_btn.setToolTip('Instalar como aplicación web')
        self.install_pwa_btn.setFixedSize(30, 30)
        self.install_pwa_btn.clicked.connect(self._install_pwa)
        self.install_pwa_btn.hide()
        self.navbar.addWidget(self.install_pwa_btn)
        
        # Añadir elementos al layout
        self.layout.addWidget(self.navbar)
        self.layout.addWidget(self.webview)
        self.setLayout(self.layout)
        self.webview.setUrl(QUrl('https://duckduckgo.com'))
        
        # Configurar el manejador de PWAs
        self.pwa_handler = PWAHandler(self.webview.page())
        self.pwa_handler.manifestFound.connect(self._on_manifest_found)
        
        # Conectar señales para verificar PWA cuando la página termina de cargar
        self.webview.loadFinished.connect(self._check_pwa_availability)
        
        # Almacenar el manifest actual
        self.current_manifest = None
    
    def _check_pwa_availability(self):
        """Verifica si el sitio actual puede ser instalado como PWA"""
        self.pwa_handler.check_pwa_support()
    
    def _on_manifest_found(self, manifest):
        """Maneja cuando se encuentra un manifest válido"""
        self.current_manifest = manifest
        if manifest:
            self.parent().pwa_action.setEnabled(True)
            self.parent().pwa_action.setToolTip('Instalar este sitio como aplicación')
            self.parent().pwa_action.setVisible(True)  # Mostrar el botón
        else:
            self.parent().pwa_action.setEnabled(False)
            self.parent().pwa_action.setToolTip('Este sitio no se puede instalar como aplicación')
            self.parent().pwa_action.setVisible(False)  # Ocultar el botón
        self.pwaAvailable.emit(manifest)
    
    def _install_pwa(self):
        """Maneja la instalación de la PWA"""
        # La instalación ahora se maneja completamente en MainWindow.install_current_pwa()
        print("[DEBUG] BrowserTab._install_pwa: Delegando instalación a MainWindow")

class HistoryWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle('Historial de Navegación')
        self.setWindowModality(Qt.NonModal)
        self.setMinimumWidth(300)
        self.setMinimumHeight(300)
        self.resize(500, 500)
        
        # Variable para rastrear la última URL cargada
        self._last_loaded_url = None
        
        # Aplicar tema oscuro
        self.setStyleSheet('''
            QDialog {
                background-color: #232323;
                color: #eee;
            }
            QListWidget {
                background-color: #2c2c2c;
                border: 1px solid #444;
                color: #eee;
            }
            QLabel {
                color: #eee;
            }
            QPushButton {
                background-color: #2c2c2c;
                color: #eee;
                border: 1px solid #444;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QLineEdit {
                background-color: #2c2c2c;
                color: #eee;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 3px;
            }
        ''')
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Barra superior
        top_bar = QHBoxLayout()
        
        # Campo de búsqueda
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('Buscar en el historial...')
        self.search_box.textChanged.connect(self.filter_history)
        
        # Botón de limpiar historial
        btn_clear = QPushButton('Limpiar Historial')
        btn_clear.clicked.connect(self.clear_history)
        
        top_bar.addWidget(self.search_box)
        top_bar.addWidget(btn_clear)
        layout.addLayout(top_bar)
        
        # Lista de historial
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.open_url)
        layout.addWidget(self.list_widget)
        
        # Cargar historial inicial
        self.load_history()
    
    def load_history(self):
        """Carga el historial en la lista"""
        self.list_widget.clear()
        if not hasattr(self.parent, 'history') or not self.parent.history:
            # Mostrar mensaje de no hay historial
            item = QListWidgetItem()
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(10, 5, 10, 5)
            
            msg_label = QLabel("No hay historial de navegación")
            msg_label.setStyleSheet('color: #888; font-style: italic;')
            layout.addWidget(msg_label)
            
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            return
            
        for entry in self.parent.history:
            item = QListWidgetItem()
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(10, 5, 10, 5)
            
            # Título y URL
            title_label = QLabel(entry['title'])
            title_label.setStyleSheet('font-size: 13px; font-weight: bold;')
            url_label = QLabel(entry['url'])
            url_label.setStyleSheet('font-size: 11px; color: #888;')
            
            # Fecha y contador de visitas
            from datetime import datetime
            timestamp = datetime.fromisoformat(entry['timestamp'])
            date_str = timestamp.strftime('%d/%m/%Y %H:%M')
            visits = entry.get('visit_count', 1)
            info_label = QLabel(f'Visitado: {date_str} - {visits} {"vez" if visits == 1 else "veces"}')
            info_label.setStyleSheet('font-size: 10px; color: #666;')
            
            layout.addWidget(title_label)
            layout.addWidget(url_label)
            layout.addWidget(info_label)
            
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
    
    def filter_history(self):
        """Filtra el historial según el texto de búsqueda"""
        search_text = self.search_box.text().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            text = ''
            for label in widget.findChildren(QLabel):
                text += label.text().lower() + ' '
            item.setHidden(search_text not in text)
    
    def clear_history(self):
        """Limpia todo el historial"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            'Confirmar',
            '¿Estás seguro de que quieres borrar todo el historial de navegación?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.parent.history.clear()
            self.parent.save_history()
            self.load_history()
    
    def open_url(self, item):
        """Abre la URL seleccionada en una nueva pestaña"""
        widget = self.list_widget.itemWidget(item)
        if widget and widget.findChildren(QLabel):
            url_label = widget.findChildren(QLabel)[1]  # La URL está en el segundo QLabel
            if url_label:
                url = url_label.text()
                if url and not url.startswith("No hay historial"):
                    self.parent.add_new_tab(QUrl(url))

class DownloadsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Descargas')
        self.setWindowModality(Qt.NonModal)
        self.setMinimumWidth(500)  # Ventana más ancha
        self.setMinimumHeight(200)  # Ventana más alta
        self.resize(700, 400)      # Tamaño inicial preferido
        
        # Aplicar tema oscuro
        self.setStyleSheet('''
            QDialog {
                background-color: #232323;
                color: #eee;
            }
            QListWidget {
                background-color: #2c2c2c;
                border: 1px solid #444;
                color: #eee;
            }
            QLabel {
                color: #eee;
            }
            QPushButton {
                background-color: #2c2c2c;
                color: #eee;
                border: 1px solid #444;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #444;
            }
            QPushButton:disabled {
                background-color: #1c1c1c;
                color: #666;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                background-color: #2c2c2c;
                color: #eee;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0a84ff;
                border-radius: 2px;
            }
        ''')
        
        # Layout principal
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # Barra superior con título y botón de limpiar
        top_bar = QHBoxLayout()
        title_label = QLabel('Historial de Descargas')
        title_label.setStyleSheet('''
            QLabel {
                color: #eee;
                font-size: 14px;
                font-weight: bold;
            }
        ''')
        
        self.clear_button = QPushButton('Limpiar Historial')
        self.clear_button.setStyleSheet('''
            QPushButton {
                background-color: #2c2c2c;
                color: #eee;
                border: 1px solid #444;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #666;
            }
            QPushButton:pressed {
                background-color: #444;
            }
        ''')
        self.clear_button.clicked.connect(self.clear_history)
        
        top_bar.addWidget(title_label)
        top_bar.addStretch()
        top_bar.addWidget(self.clear_button)
        self.layout.addLayout(top_bar)
        
        # Lista de descargas
        self.list_widget = QListWidget()
        self.list_widget.setSpacing(5)  # Espacio entre elementos
        self.layout.addWidget(self.list_widget)
        
        self.download_items = {}  # id: widgets

    def clear_history(self):
        """Limpia el historial de descargas"""
        from PyQt5.QtWidgets import QMessageBox
        
        # Confirmar con el usuario
        reply = QMessageBox.question(
            self,
            'Confirmar',
            '¿Estás seguro de que quieres limpiar el historial de descargas?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Eliminar todos los items
            self.list_widget.clear()
            # Limpiar el diccionario de items
            self.download_items.clear()
            
    def add_download(self, qdownload):
        # Crear el widget contenedor con fondo oscuro
        widget = QWidget()
        widget.setStyleSheet('QWidget { background-color: #2c2c2c; border-radius: 4px; margin: 2px; }')
        
        # Layout horizontal con márgenes para mejor apariencia
        hbox = QHBoxLayout(widget)
        hbox.setContentsMargins(15, 10, 15, 10)
        hbox.setSpacing(15)
        
        # Etiqueta del archivo con nombre y estado
        filename = qdownload.downloadFileName()
        # Truncar el nombre si es muy largo (máximo 40 caracteres)
        if len(filename) > 40:
            # Separar el nombre y la extensión
            import os
            name, ext = os.path.splitext(filename)
            # Truncar el nombre dejando espacio para la extensión y los ...
            truncated = name[:37 - len(ext)] + "..." + ext
            display_name = truncated
        else:
            display_name = filename
            
        label = QLabel(display_name)
        label.setStyleSheet('''
            color: #eee;
            font-size: 12px;
        ''')
        # Configurar tooltip para mostrar el nombre completo al pasar el mouse
        label.setToolTip(filename)
        label.setMinimumWidth(250)  # Más espacio para el nombre
        label.setMaximumWidth(400)  # Limitar el ancho máximo
        
        # Barra de progreso con estilo mejorado
        progress = QProgressBar()
        progress.setMinimumWidth(250)
        progress.setMaximumWidth(350)
        progress.setMinimumHeight(20)  # Altura fija para mejor apariencia
        progress.setValue(0)
        progress.setFormat("%p% - %v/%m bytes")  # Mostrar porcentaje y bytes
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
                color: #eee;
                background-color: #2c2c2c;
            }
            QProgressBar::chunk {
                background-color: #0a84ff;
                border-radius: 2px;
            }
        """)
        
        # Botones de control
        btn_pause = QPushButton('Pausar')
        btn_resume = QPushButton('Continuar')
        btn_cancel = QPushButton('Cancelar')
        
        # Estilo para los botones
        button_style = """
            QPushButton {
                background-color: #2c2c2c;
                color: #eee;
                border: 1px solid #444;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #444;
            }
            QPushButton:disabled {
                background-color: #1c1c1c;
                color: #666;
            }
        """
        btn_pause.setStyleSheet(button_style)
        btn_resume.setStyleSheet(button_style)
        btn_cancel.setStyleSheet(button_style)
        
        # Agregar widgets al layout
        hbox.addWidget(label, stretch=1)  # La etiqueta se estirará
        hbox.addWidget(progress)
        hbox.addWidget(btn_pause)
        hbox.addWidget(btn_resume)
        hbox.addWidget(btn_cancel)
        
        # Crear y agregar item a la lista
        item = QListWidgetItem()
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        item.setSizeHint(widget.sizeHint())
        
        # Conectar señales de control y manejar estados
        def on_pause_clicked():
            qdownload.pause()
            btn_pause.setEnabled(False)
            btn_resume.setEnabled(True)
            label.setText(f"{qdownload.downloadFileName()} (Pausado)")
            label.setStyleSheet('color: #ffd93d;')  # Amarillo para pausado
            
        def on_resume_clicked():
            qdownload.resume()
            btn_pause.setEnabled(True)
            btn_resume.setEnabled(False)
            label.setText(qdownload.downloadFileName())
            label.setStyleSheet('color: #eee;')  # Color normal al reanudar
            
        btn_pause.clicked.connect(on_pause_clicked)
        btn_resume.clicked.connect(on_resume_clicked)
        btn_cancel.clicked.connect(qdownload.cancel)
        
        # Actualizar progreso y estado de botones
        def on_progress(received, total):
            if total > 0:
                percent = int(received * 100 / total)
                progress.setValue(percent)
                # Mostrar información detallada del progreso
                mb_received = received / 1024 / 1024  # Convertir a MB
                mb_total = total / 1024 / 1024
                progress.setFormat(f"{percent}% - {mb_received:.1f}MB/{mb_total:.1f}MB")
            else:
                progress.setValue(0)
                progress.setFormat("Descargando...")
            # Asegurarse de que el botón de pausa esté habilitado durante la descarga
            if qdownload.state() == qdownload.DownloadInProgress:
                btn_pause.setEnabled(True)
                btn_resume.setEnabled(False)
        
        # Estado final
        def on_finished():
            if qdownload.state() == qdownload.DownloadCompleted:
                label.setText(f"{qdownload.downloadFileName()} (Completado)")
                label.setStyleSheet('color: #00ff00;')  # Verde para descargas completadas
                progress.setStyleSheet(progress.styleSheet() + "QProgressBar::chunk { background-color: #00aa00; }")
            elif qdownload.state() == qdownload.DownloadCancelled:
                label.setText(f"{qdownload.downloadFileName()} (Cancelado)")
                label.setStyleSheet('color: #ff6b6b;')  # Rojo para descargas canceladas
                progress.setStyleSheet(progress.styleSheet() + "QProgressBar::chunk { background-color: #aa0000; }")
            elif qdownload.state() == qdownload.DownloadInterrupted:
                label.setText(f"{qdownload.downloadFileName()} (Interrumpido)")
                label.setStyleSheet('color: #ffd93d;')  # Amarillo para descargas interrumpidas
                progress.setStyleSheet(progress.styleSheet() + "QProgressBar::chunk { background-color: #aaaa00; }")
            btn_pause.setEnabled(False)
            btn_resume.setEnabled(False)
            btn_cancel.setEnabled(False)
        
        # Conectar señales principales
        qdownload.downloadProgress.connect(on_progress)
        qdownload.finished.connect(on_finished)
        
        # Guardar referencia
        self.download_items[id(qdownload)] = (item, widget, progress, btn_pause, btn_resume, btn_cancel)

class MainWindow(QMainWindow):
    # Define signals with correct types
    suggestions_ready = pyqtSignal(list)
    suggestions_hide = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Inicializar variables de las ventanas
        self._history_window = None
        self._downloads_window = None
        self._windows = []  # Lista para mantener referencia a todas las ventanas
        
        # Configurar ventana sin bordes
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint)
        
        self.setWindowTitle('Fennex Browser')
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.icons_path = os.path.join(BASE_DIR, "icons/") + os.sep
        self.setWindowIcon(QIcon('icons/icon.png'))
                
        # El tamaño se restaurará en load_config
        self.icons_path = 'icons/'
        
        # Cargar configuración y datos
        self.load_config()
        self.load_encrypted_passwords()
        self.load_bookmarks()
        self.load_history()  # Cargar el historial
        
        # Variables para manejar el arrastre de la ventana
        self._pressed = False
        self._start_pos = None
        self._original_pos = None
        
        # Asegurar que los diálogos nuevos usen el tema actual
        from PyQt5.QtWidgets import QDialog
        original_dialog_init = QDialog.__init__
        def themed_dialog_init(dialog_self, *args, **kwargs):
            original_dialog_init(dialog_self, *args, **kwargs)
            if hasattr(self, 'theme_class'):
                self.apply_theme_to_widget(dialog_self)
        QDialog.__init__ = themed_dialog_init
        # Configurar el widget de pestañas
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Aplicar estilo al QTabWidget y su contenedor
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #232323;
            }
            QWidget#tabs {
                background-color: #232323;
            }
            QTabWidget::tab-bar {
                alignment: left;
                background-color: #232323;
            }
            QTabBar::tab {
                background-color: #2c2c2c;
                color: #aaa;
                padding: 4px 4px;
                min-width: 30px;
                max-width: 70px;
                margin-right: 1px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #353535;
                color: #fff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #303030;
            }
            QTabBar::close-button {
                BASE_DIR = os.path.dirname(os.path.abspath(__file__))
                self.icons_path = os.path.join(BASE_DIR, "icons/") + os.sep
                image: url(""" + self.icons_path + """close.png');
                subcontrol-position: right;
            }
            QTabBar::close-button:hover {
                background-color: transparen;
                border-radius: 2px;
            }
        """)
        self.tabs.setObjectName("tabs")
        
        self.setCentralWidget(self.tabs)
        self.create_toolbar()
        self.add_new_tab(QUrl(self.homepage), 'Nueva pestaña')
        self.add_newtab_button_tab()
        self.set_dark_theme()
        
        # Configurar el perfil global de descargas
        from PyQt5.QtWebEngineWidgets import QWebEngineProfile, QWebEnginePage
        from PyQt5.QtCore import QStandardPaths
        
        # Obtener y configurar el perfil global
        profile = QWebEngineProfile.defaultProfile()
        
        # Establecer la carpeta de descargas predeterminada
        downloads_path = os.path.expanduser('~/Descargas')
        if not os.path.exists(downloads_path):
            try:
                os.makedirs(downloads_path)
            except Exception:
                downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
                if not downloads_path:
                    downloads_path = os.path.expanduser('~')
        
        # Configurar las rutas del perfil
        self.download_path = downloads_path
        profile.setCachePath(os.path.join(downloads_path, '.cache'))
        profile.setPersistentStoragePath(os.path.join(downloads_path, '.storage'))
        profile.setDownloadPath(downloads_path)
        
        # Habilitar el almacenamiento persistente
        profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)
        
        # Conectar la señal de descarga
        profile.downloadRequested.connect(self.on_download_requested)
        print(f"Perfil configurado con ruta de descargas: {downloads_path}")
        
        # Connect signals properly
        self.suggestions_ready.connect(self.show_suggestions)
        self.suggestions_hide.connect(self.hide_suggestions)

    ENCRYPTED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyqt_chrome_passwords.enc')
    MASTER_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pyqt_chrome_masterkey.enc')
    
    def save_master_password(self):
        # Guarda la contraseña maestra encriptada en archivo
        if hasattr(self, 'master_password') and self.master_password:
            try:
                from cryptography.fernet import Fernet
                import base64, hashlib
                key = hashlib.sha256(b'pyqt_chrome_masterkey').digest()
                key = base64.urlsafe_b64encode(key)
                f = Fernet(key)
                enc = f.encrypt(self.master_password.encode())
                with open(self.MASTER_KEY_FILE, 'wb') as mf:
                    mf.write(enc)
            except Exception:
                pass

    def load_master_password(self):
        # Carga la contraseña maestra encriptada desde archivo
        try:
            if os.path.exists(self.MASTER_KEY_FILE):
                from cryptography.fernet import Fernet
                import base64, hashlib
                key = hashlib.sha256(b'pyqt_chrome_masterkey').digest()
                key = base64.urlsafe_b64encode(key)
                f = Fernet(key)
                with open(self.MASTER_KEY_FILE, 'rb') as mf:
                    enc = mf.read()
                self.master_password = f.decrypt(enc).decode()
        except Exception:
            self.master_password = None

    def delete_master_password(self):
        # Borra el archivo de la contraseña maestra
        try:
            if os.path.exists(self.MASTER_KEY_FILE):
                os.remove(self.MASTER_KEY_FILE)
            self.master_password = None
        except Exception:
            pass

    def encrypt_data(self, data, password):
        try:
            from cryptography.fernet import Fernet
            import base64, hashlib
            key = hashlib.sha256(password.encode()).digest()
            key = base64.urlsafe_b64encode(key)
            f = Fernet(key)
            return f.encrypt(data.encode())
        except Exception:
            return None

    def decrypt_data(self, enc_data, password):
        try:
            from cryptography.fernet import Fernet
            import base64, hashlib
            key = hashlib.sha256(password.encode()).digest()
            key = base64.urlsafe_b64encode(key)
            f = Fernet(key)
            return f.decrypt(enc_data).decode()
        except Exception:
            return None

    def save_encrypted_passwords(self):
        # Guarda cuentas en archivo cifrado (sin guardar la clave maestra aquí)
        import json
        if hasattr(self, 'master_password') and self.master_password:
            data = json.dumps({
                'accounts': getattr(self, 'accounts', [])
            })
            enc = self.encrypt_data(data, self.master_password)
            if enc:
                with open(self.ENCRYPTED_FILE, 'wb') as f:
                    f.write(enc)
        self.save_master_password()

    def load_encrypted_passwords(self):
        # Carga cuentas desde archivo cifrado, y la clave maestra desde su propio archivo
        import json
        self.load_master_password()
        self.accounts = []
        self._encrypted_accounts_data = None
        if os.path.exists(self.ENCRYPTED_FILE):
            try:
                with open(self.ENCRYPTED_FILE, 'rb') as f:
                    enc = f.read()
                self._encrypted_accounts_data = enc
            except Exception:
                self._encrypted_accounts_data = None

    def prompt_save_credentials(self, browser):
        # Inyecta JS para detectar envío de formulario de login y pregunta si guardar credenciales
        js = '''
        (function() {
            var forms = document.querySelectorAll('form');
            for (var i = 0; i < forms.length; i++) {
                forms[i].addEventListener('submit', function(e) {
                    var user = this.querySelector('input[type="email"],input[type="text"]');
                    var pass = this.querySelector('input[type="password"]');
                    if (user && pass && user.value && pass.value) {
                        window.saveCredentials && window.saveCredentials(user.value, pass.value);
                    }
                });
            }
        })();
        '''
        # Expone una función a JS para guardar credenciales
        class SaveCreds:
            def __init__(self, outer):
                self.outer = outer
            def __call__(self, usuario, password):
                from PyQt5.QtWidgets import QInputDialog
                dominio, ok = QInputDialog.getText(self.outer, 'Guardar contraseña', 'Dominio para asociar (ej: gmail.com):')
                if ok and dominio:
                    import base64
                    encoded = base64.b64encode(password.encode('utf-8')).decode('utf-8')
                    if not any(a['usuario'] == usuario and a['dominio'] == dominio for a in self.outer.accounts):
                        self.outer.accounts.append({'usuario': usuario, 'password': encoded, 'dominio': dominio})
        browser.page().setWebChannel(None)
        try:
            from PyQt5.QtWebChannel import QWebChannel
            channel = QWebChannel()
            save_creds = SaveCreds(self)
            channel.registerObject('saveCredentials', save_creds)
            browser.page().setWebChannel(channel)
            browser.page().runJavaScript(js)
        except Exception:
            pass

    def inject_credentials(self, url):
        # Autocompleta formularios de login si hay credenciales guardadas para el dominio
        from urllib.parse import urlparse
        import base64
        domain = urlparse(url.toString()).netloc
        for acc in getattr(self, 'accounts', []):
            if domain and acc.get('dominio') and acc['dominio'] in domain:
                password = base64.b64decode(acc['password']).decode('utf-8')
                js = (
                    f"var userInput = document.querySelector('input[type=\"email\"],input[type=\"text\"]');"
                    f"var passInput = document.querySelector('input[type=\"password\"]');"
                    f"if(userInput){{userInput.value = '{acc['usuario']}';}}"
                    f"if(passInput){{passInput.value = '{password}';}}"
                )
                try:
                    self.current_webview().page().runJavaScript(js)
                except Exception:
                    pass
                break

    import os, json
    CONFIG_FILE = os.path.expanduser('~/.pyqt_chrome_config.json')
    HISTORY_FILE = os.path.expanduser('~/.pyqt_chrome_history.json')
    
    def load_history(self):
        """Carga el historial de navegación desde el archivo"""
        self.history = []
        if os.path.exists(self.HISTORY_FILE):
            try:
                with open(self.HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
            except Exception as e:
                print(f"Error al cargar el historial: {e}")
                self.history = []
    
    def save_history(self):
        """Guarda el historial de navegación en el archivo"""
        try:
            with open(self.HISTORY_FILE, 'w') as f:
                json.dump({'history': self.history}, f)
        except Exception as e:
            print(f"Error al guardar el historial: {e}")
    
    def add_to_history(self, url, title=''):
        """Añade una entrada al historial"""
        from datetime import datetime
        
        # Asegurarse de que self.history es una lista
        if not hasattr(self, 'history') or self.history is None:
            self.history = []
        
        # Ignorar páginas about: y URLs vacías
        if not url or url.toString().startswith('about:'):
            return
            
        # Crear entrada con timestamp
        entry = {
            'url': url.toString(),
            'title': title or url.toString(),  # Usar URL si no hay título
            'timestamp': datetime.now().isoformat(),
            'visit_count': 1
        }
        
        # Buscar si la URL ya existe
        found = False
        for i, existing in enumerate(self.history):
            # Verificar que existing sea un diccionario
            if not isinstance(existing, dict):
                continue
                
            if existing.get('url') == entry['url']:
                # Actualizar entrada existente
                self.history[i] = {
                    'url': existing['url'],
                    'title': title or existing.get('title', ''),
                    'timestamp': entry['timestamp'],
                    'visit_count': existing.get('visit_count', 0) + 1
                }
                found = True
                break
        
        if not found:
            # Si no existe, añadir al principio
            self.history.insert(0, entry)
            
            # Limitar el historial a 1000 entradas
            while len(self.history) > 1000:
                self.history.pop()
        
        # Limpiar entradas inválidas
        self.history = [h for h in self.history if isinstance(h, dict) and 'url' in h]
            
        # Guardar el historial actualizado
        try:
            self.save_history()
        except Exception as e:
            print(f"Error al guardar el historial: {e}")

    def load_config(self):
        # Cargar la configuración del archivo
        config = {}
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"Configuración cargada desde: {self.CONFIG_FILE}")
                print(f"Contenido: {config}")
        except Exception as e:
            print(f"Error al leer el archivo de configuración: {e}")
            config = {}

        # Cargar valores con fallback a configuración predeterminada
        self.homepage = config.get('homepage', 'https://duckduckgo.com')
        self.search_engine = 'https://duckduckgo.com/?q='
        self.proxy_host = config.get('proxy_host', '')
        self.proxy_port = config.get('proxy_port', '')

        # Restaurar tamaño de ventana
        w = config.get('window_width', 1200)
        h = config.get('window_height', 800)
        self.resize(w, h)

        # Cargar y aplicar el tema guardado
        saved_theme = config.get('theme')
        saved_theme_class = config.get('theme_class')
        
        if saved_theme and saved_theme_class:
            print(f"Cargando tema guardado: {saved_theme} ({saved_theme_class})")
            self.current_theme = saved_theme
            self.theme_class = saved_theme_class
        else:
            print("Usando tema predeterminado")
            self.current_theme = 'Oscuro'
            self.theme_class = 'theme-dark'

        # Asegurar que el tema se aplique después de que la interfaz se haya inicializado
        QTimer.singleShot(100, self.apply_theme)

    def save_config(self):
        # Recopilar la configuración actual
        config = {
            'homepage': getattr(self, 'homepage', 'https://duckduckgo.com'),
            'search_engine': 'https://duckduckgo.com/?q=',  # Motor de búsqueda fijo
            'proxy_host': getattr(self, 'proxy_host', ''),
            'proxy_port': getattr(self, 'proxy_port', ''),
            # Guardar tamaño de ventana
            'window_width': self.width(),
            'window_height': self.height()
        }
        
        # Guardar configuración del tema
        if hasattr(self, 'current_theme') and hasattr(self, 'theme_class'):
            config.update({
                'theme': self.current_theme,
                'theme_class': self.theme_class
            })
            print(f"Guardando tema en configuración: {self.current_theme} ({self.theme_class})")
        
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f)
            print("Configuración guardada exitosamente")
        except Exception as e:
            print(f"Error al guardar la configuración: {e}")

    def add_newtab_button_tab(self):
        # Añade una pestaña especial con el icono de nueva pestaña y menos ancho
        newtab_widget = QWidget()
        self.tabs.addTab(newtab_widget, QIcon(self.icons_path + 'newtab.png'), '')
        tabbar = self.tabs.tabBar()
        tabbar.setTabButton(self.tabs.count()-1, tabbar.RightSide, None)
        tabbar.tabBarClicked.connect(self.handle_tabbar_click)
        # Estilo para el botón de nueva pestaña
        tabbar.setStyleSheet(self.get_tabbar_stylesheet())

    def get_tabbar_stylesheet(self):
        # Estilo avanzado tipo Chrome para pestañas y botón de nueva pestaña
        return """
        QTabWidget::pane {
            border: none;
            background-color: #232323;
        }
        QTabBar {
            background: #232323;
            border: none;
        }
        QTabBar::tab {
            background: #2c2c2c;
            color: #eee;
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 8px 25px;
            min-width: 150px;
            max-width: 200px;
            margin-right: 2px;
            margin-top: 5px;
        }
        QTabBar::tab:hover {
            background: #3a3a3a;
        }
        QTabBar::tab:selected {
            background: #444;
            color: #fff;
            border-bottom: 2px solid #232323;
        }
        QTabBar::tab:!selected {
            background: #2c2c2c;
            color: #bbb;
        }
        QTabBar::tab:last {
            min-width: 36px;
            max-width: 36px;
            padding: 0px 0px 0px 0px;
            margin-left: 8px;
            background: #232323;
            border: none;
            border-radius: 50%;
        }
        QTabBar {
            border-bottom: 1px solid #444;
            background: #232323;
        }
        """

    def handle_tabbar_click(self, index):
        # Si se hace clic en la pestaña de nueva pestaña, abrir una nueva y mover el botón
        if index == self.tabs.count() - 1:
            self.add_new_tab(QUrl('https://duckduckgo.com'), 'Nueva pestaña')
            self.tabs.setCurrentIndex(self.tabs.count() - 2)
            self.tabs.removeTab(self.tabs.count() - 1)
            self.add_newtab_button_tab()

    def set_dark_theme(self):
        dark_stylesheet = """
        QMainWindow {
            background-color: #232323;
        }
        QToolBar {
            background: #2c2c2c;
            border-bottom: 1px solid #444;
        }
        QTabWidget::pane {
            border: 1px solid #444;
            background: #232323;
        }
        QTabBar::tab {
            background: #2c2c2c;
            color: #eee;
            border: 1px solid #444;
            padding: 8px;
            min-width: 120px;
        }
        QTabBar::tab:selected {
            background: #444;
            color: #fff;
        }
        QTabBar::tab:!selected {
            background: #2c2c2c;
            color: #bbb;
        }
        QLineEdit {
            background: #232323;
            color: #eee;
            border: 1px solid #444;
            padding: 4px;
        }
        """
        self.setStyleSheet(dark_stylesheet)

    def show_history(self):
        """Muestra la ventana de historial"""
        if not self._history_window:
            self._history_window = HistoryWindow(self)
        self._history_window.show()
        self._history_window.raise_()
        self._history_window.activateWindow()
        
    def mouseDoubleClickEvent(self, event):
        """Maneja el doble clic para maximizar/restaurar"""
        if event.button() == Qt.LeftButton:
            if event.y() < 50:  # Solo en la barra de herramientas
                self.toggle_maximize()

    def mousePressEvent(self, event):
        """Maneja el evento de presionar el mouse para mover la ventana"""
        if event.button() == Qt.LeftButton:
            # Solo permitir arrastrar desde la barra de herramientas
            if event.y() < 50:  # Altura aproximada de la barra de herramientas
                self._pressed = True
                self._start_pos = event.globalPos()
                self._original_pos = self.pos()

    def mouseReleaseEvent(self, event):
        """Maneja el evento de soltar el mouse"""
        self._pressed = False

    def mouseMoveEvent(self, event):
        """Maneja el evento de mover el mouse para arrastrar la ventana"""
        if self._pressed:
            delta = event.globalPos() - self._start_pos
            self.move(self._original_pos + delta)
            
    def toggle_maximize(self):
        """Alterna entre ventana maximizada y restaurada"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
            
    def create_toolbar(self):
        from PyQt5.QtWidgets import QFrame, QListWidget, QVBoxLayout, QStyle, QStyleOption
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPainter, QColor
        
        # Crear contenedor principal para la barra de título y herramientas
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet('''
            QWidget {
                background-color: #232323;
                border: none;
            }
        ''')
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(5, 0, 5, 0)
        title_layout.setSpacing(2)
        
        # Botones de ventana (minimizar, maximizar, cerrar)
        btn_style = '''
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 0px;
                min-width: 40px;
                max-width: 40px;
                min-height: 40px;
                max-height: 40px;
                color: #ddd;
            }
            QPushButton:hover { background-color: #404040; }
        '''
        
        btn_min = QPushButton('🗕')
        btn_max = QPushButton('🗖')
        btn_close = QPushButton('✕')
        
        btn_min.setStyleSheet(btn_style)
        btn_max.setStyleSheet(btn_style)
        btn_close.setStyleSheet(btn_style + "QPushButton:hover { background-color: #c42b1c; }")
        
        btn_min.clicked.connect(self.showMinimized)
        btn_max.clicked.connect(self.toggle_maximize)
        btn_close.clicked.connect(self.close)
        
        # Crear la barra de herramientas principal
        toolbar = QToolBar('Navegación')
        self.addToolBar(Qt.TopToolBarArea, toolbar)  # Fijar en la parte superior
        
        # Hacer la barra no movible y no flotante
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        # Establecer estilo para que parezca más integrada
        toolbar.setStyleSheet('''
            QToolBar {
                background: #232323;
                border: none;
                border-bottom: 1px solid #444;
                padding: 5px;
                spacing: 5px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #404040;
            }
            QLineEdit {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                color: #fff;
                padding: 5px;
                selection-background-color: #0078d7;
            }
            QLineEdit:focus {
                border-color: #0078d7;
            }
        ''')
        
        # Botón atrás
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.icons_path = os.path.join(BASE_DIR, "icons/") + os.sep
        back_action = QAction(QIcon(self.icons_path + 'back.png'), 'Atrás', self)
        back_action.triggered.connect(lambda: self.current_webview().back())
        toolbar.addAction(back_action)
        
        # Botón adelante
        forward_action = QAction(QIcon(self.icons_path + 'forward.png'), 'Adelante', self)
        forward_action.triggered.connect(lambda: self.current_webview().forward())
        toolbar.addAction(forward_action)
        
        # Botón recargar
        reload_action = QAction(QIcon(self.icons_path + 'reload.png'), 'Recargar', self)
        reload_action.triggered.connect(lambda: self.current_webview().reload())
        toolbar.addAction(reload_action)
        
        # Botón inicio
        home_action = QAction(QIcon(self.icons_path + 'home.png'), 'Inicio', self)
        home_action.triggered.connect(self.navigate_home)
        toolbar.addAction(home_action)
        
        # Barra de direcciones
        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        toolbar.addWidget(self.urlbar)

        # Botón Ir
        go_action = QAction(QIcon(self.icons_path + 'go.png'), 'Ir', self)
        go_action.triggered.connect(self.navigate_to_url)
        toolbar.addAction(go_action)

        # Botón PWA (inicialmente oculto)
        self.pwa_action = QAction(QIcon(self.icons_path + 'extension.png'), 'Instalar como aplicación', self)
        self.pwa_action.triggered.connect(self.install_current_pwa)
        self.pwa_action.setEnabled(False)  # Inicialmente deshabilitado
        self.pwa_action.setToolTip('Este sitio no se puede instalar como aplicación')
        self.pwa_action.setVisible(False)  # Inicialmente oculto
        toolbar.addAction(self.pwa_action)

        # Botón Marcador
        bookmark_action = QAction(QIcon(self.icons_path + 'bookmark.png'), 'Agregar a Marcadores', self)
        bookmark_action.triggered.connect(self.add_bookmark)
        toolbar.addAction(bookmark_action)

        # Botón Traductor
        translator_action = QAction(QIcon(self.icons_path + 'traductor.png'), 'Traducir', self)
        translator_action.triggered.connect(self.translate_page)
        toolbar.addAction(translator_action)

        # Popup de sugerencias tipo menú contextual
        self.suggest_popup = QFrame(self)
        self.suggest_popup.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.suggest_popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.suggest_popup.setStyleSheet("""
            QFrame {
                background: #fffae6; 
                color: #232323; 
                border: 2px solid #ff9800;
                border-radius: 4px;
            }
        """)
        self.suggest_list = QListWidget(self.suggest_popup)
        self.suggest_list.setStyleSheet("""
            QListWidget {
                background: #fffae6; 
                color: #232323; 
                border: none;
                selection-background-color: #ff9800;
                selection-color: white;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:hover {
                background: #fff3cd;
            }
        """)
        layout = QVBoxLayout(self.suggest_popup)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.suggest_list)
        self.suggest_popup.setLayout(layout)
        self.suggest_popup.hide()
        print(f"[DEBUG] Popup initialized: {self.suggest_popup}")
        print(f"[DEBUG] Popup parent: {self.suggest_popup.parent()}")

        # Debounce para sugerencias
        self._suggest_timer = QTimer(self)
        self._suggest_timer.setSingleShot(True)
        self._suggest_timer.timeout.connect(lambda: self.on_entry_changed(self.urlbar.text()))
        self.urlbar.textEdited.connect(self._on_urlbar_text_edited)

        # Mostrar sugerencias al ganar foco si hay texto
        def focus_in(event):
            QLineEdit.focusInEvent(self.urlbar, event)
            if self.urlbar.text().strip():
                self.on_entry_changed(self.urlbar.text())
        self.urlbar.focusInEvent = focus_in

        # Ocultar sugerencias al perder foco con delay
        def focus_out(event):
            QLineEdit.focusOutEvent(self.urlbar, event)
            QTimer.singleShot(150, self.hide_suggestions)
        self.urlbar.focusOutEvent = focus_out

        # Selección de sugerencia
        def on_suggestion_clicked(item):
            text = item.text()
            print(f"[DEBUG] Suggestion clicked: {text}")
            self.urlbar.setText(text)
            self.hide_suggestions()
            self.urlbar.setFocus()
            self.navigate_to_url()
        self.suggest_list.itemClicked.connect(on_suggestion_clicked)
        self.suggest_list.itemDoubleClicked.connect(on_suggestion_clicked)
        # Evitar que el popup se oculte si la lista tiene foco
        self.suggest_list.focusOutEvent = lambda event: (self.hide_suggestions() if not self.suggest_popup.underMouse() else None)

        # Navegación con teclas
        self.urlbar.keyPressEvent = self._urlbar_keypress_event
        
        # Mostrar sugerencias al ganar foco si hay texto (opcional, pero sin ocultar por perder foco)
        def focus_in(event):
            QLineEdit.focusInEvent(self.urlbar, event)
            if self.urlbar.text().strip():
                self.on_entry_changed(self.urlbar.text())
        self.urlbar.focusInEvent = focus_in

        # Selección de sugerencia
        def on_suggestion_clicked(item):
            text = item.text()
            print(f"[DEBUG] Suggestion clicked: {text}")
            self.urlbar.setText(text)
            self.hide_suggestions()
            self.navigate_to_url()
        self.suggest_list.itemClicked.connect(on_suggestion_clicked)
        self.suggest_list.itemDoubleClicked.connect(on_suggestion_clicked)
    # Ya no se oculta el popup por perder foco
    # self.suggest_list.focusOutEvent = lambda event: (self.hide_suggestions() if not self.suggest_popup.underMouse() else None)

        # Navegación con teclas
        self.urlbar.keyPressEvent = self._urlbar_keypress_event

        # Botón de descargas
        downloads_action = QAction(QIcon(self.icons_path + 'download.png'), 'Descargas', self)
        downloads_action.triggered.connect(self.show_downloads)
        toolbar.addAction(downloads_action)
        
        # Botón de menú contextual
        menu_button = QToolButton()
        menu_button.setIcon(QIcon(self.icons_path + 'menu.png'))
        menu_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu()
        # Tema oscuro para el menú contextual
        menu.setStyleSheet('''
            QMenu { 
                background-color: #232323; 
                color: #eee; 
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item { 
                background-color: #232323; 
                color: #eee;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected { 
                background-color: #404040;
                color: #fff;
            }
            QMenu::separator {
                height: 1px;
                background: #444;
                margin: 5px 0px;
            }
        ''')
        menu.addAction(QIcon(self.icons_path + 'newwindow.png'), 'Nueva ventana', self.open_new_window)
        
        # Acción de historial con atajo
        history_action = QAction(QIcon(self.icons_path + 'history.png'), 'Historial', self)
        history_action.setShortcut('Ctrl+H')
        history_action.triggered.connect(self.show_history)
        menu.addAction(history_action)
        
        menu.addAction(QIcon(self.icons_path + 'bookmarks.png'), 'Marcadores', self.show_bookmarks)
        menu.addAction(QIcon(self.icons_path + 'settings.png'), 'Configuración', self.show_settings)
        menu.addAction(QIcon(self.icons_path + 'about.png'), 'Acerca de', self.show_about)
        menu.addSeparator()
        menu.addAction(QIcon(self.icons_path + 'exit.png'), 'Salir', self.close)
        menu_button.setMenu(menu)
        toolbar.addWidget(menu_button)
        
        # Controles de ventana estilo macOS
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(10, 0, 5, 0)
        control_layout.setSpacing(8)  # Espaciado entre botones
        
        # Estilo base para los botones tipo macOS
        base_style = '''
            QPushButton {
                background-color: %s;
                border: none;
                border-radius: 7px;
                min-width: 15px;
                max-width: 15px;
                min-height: 15px;
                max-height: 15px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: %s;
            }
            QPushButton:pressed {
                background-color: %s;
            }
        '''
        
        # Crear los botones con sus colores específicos
        btn_close = QPushButton()
        btn_min = QPushButton()
        btn_max = QPushButton()
        
        # Establecer estilos para cada botón
        btn_min.setStyleSheet(base_style % ('#ffbd2e', '#ffc13b', '#cc9624'))    # Amarillo
        btn_max.setStyleSheet(base_style % ('#28c940', '#30d84a', '#1fa033'))    # Verde
        btn_close.setStyleSheet(base_style % ('#ff5f57', '#ff6e67', '#cc4a42'))  # Rojo
        
        # Añadir el tooltip (texto emergente) para cada botón
        btn_min.setToolTip('Minimizar')
        btn_max.setToolTip('Maximizar')
        btn_close.setToolTip('Cerrar')
        
        # Agregar los botones al layout en orden personalizado (amarillo, verde, rojo)
        control_layout.addWidget(btn_min)
        control_layout.addWidget(btn_max)
        control_layout.addWidget(btn_close)
        
        # Conectar las señales
        btn_min.clicked.connect(self.showMinimized)
        btn_max.clicked.connect(self.toggle_maximize)
        btn_close.clicked.connect(self.close)
        
        # Agregar un espaciador después de los botones
        spacer = QWidget()
        spacer.setFixedWidth(10)
        control_layout.addWidget(spacer)
        
        toolbar.addWidget(control_widget)
    def show_downloads(self):
        try:
            if not hasattr(self, '_downloads_window') or self._downloads_window is None:
                self._downloads_window = DownloadsWindow(self)
                if hasattr(self, 'theme_class'):
                    self.apply_theme_to_widget(self._downloads_window)
            self._downloads_window.show()
            self._downloads_window.raise_()
            self._downloads_window.activateWindow()
        except Exception as e:
            print(f"Error al mostrar ventana de descargas: {e}")
            # Intentar recrear la ventana si hubo un error
            self._downloads_window = None
            self.show_downloads()

    def _urlbar_keypress_event(self, event):
        if self.suggest_popup.isVisible() and self.suggest_list.count() > 0:
            if event.key() in (Qt.Key_Down, Qt.Key_Up):
                current = self.suggest_list.currentRow()
                if event.key() == Qt.Key_Down:
                    next_row = 0 if current < 0 else min(current + 1, self.suggest_list.count() - 1)
                else:
                    next_row = max(current - 1, 0)
                self.suggest_list.setCurrentRow(next_row)
                # No mover el foco, solo seleccionar visualmente
                return
            elif event.key() == Qt.Key_Escape:
                self.hide_suggestions()
                return
            elif event.key() == Qt.Key_Return and self.suggest_list.currentRow() >= 0:
                item = self.suggest_list.currentItem()
                if item:
                    self.urlbar.setText(item.text())
                    self.hide_suggestions()
                    self.urlbar.setFocus()
                    self.navigate_to_url()
                    return
        QLineEdit.keyPressEvent(self.urlbar, event)

    def _on_urlbar_text_edited(self, text):
        # Debounce: solo buscar sugerencias si el usuario deja de escribir 200ms
        self._suggest_timer.start(200)

    def on_entry_changed(self, text):
        import threading
        text = text.strip()
        if not hasattr(self, '_suggest_query_version'):
            self._suggest_query_version = 0
        self._suggest_query_version += 1
        my_version = self._suggest_query_version

        if not text:
            self.suggestions_hide.emit()
            return

        # Permitir siempre nuevas sugerencias al escribir
        self._last_suggest_text = text

        def fetch_suggestions(version):
            try:
                import requests
                url = f"https://duckduckgo.com/ac/?q={requests.utils.quote(text)}"
                res = requests.get(url, timeout=2)
                data = res.json()
                suggestions = [item['phrase'] for item in data if isinstance(item, dict) and 'phrase' in item]
                # Solo mostrar/ocultar si es la última consulta
                if self._suggest_query_version == version:
                    self.suggestions_ready.emit(suggestions)
            except Exception:
                if self._suggest_query_version == version:
                    self.suggestions_hide.emit()
        threading.Thread(target=fetch_suggestions, args=(my_version,), daemon=True).start()
    
    @pyqtSlot(list)
    def show_suggestions(self, data):
        self.suggest_list.clear()
        if not isinstance(data, list) or not data:
            self.hide_suggestions()
            return
        
        for phrase in data:
            self.suggest_list.addItem(phrase)
        
        self.suggest_list.setCurrentRow(-1)
        
        # Asegurar que el popup esté inicializado
        if not hasattr(self, 'suggest_popup') or self.suggest_popup is None:
            return
        
        # Posicionar el popup
        pos = self.urlbar.mapToGlobal(self.urlbar.rect().bottomLeft())
        height = min(200, max(120, self.suggest_list.sizeHintForRow(0) * self.suggest_list.count() + 10))
        
        self.suggest_popup.setFixedSize(self.urlbar.width(), height)
        self.suggest_popup.move(pos.x(), pos.y())
        
        # Mostrar el popup
        self.suggest_popup.setVisible(True)
        self.suggest_popup.show()
        self.suggest_popup.raise_()
    
    @pyqtSlot()
    def hide_suggestions(self):
        if hasattr(self, 'suggest_popup') and self.suggest_popup:
            self.suggest_popup.hide()

    def open_new_window(self):
        import subprocess, sys, os
        subprocess.Popen([sys.executable, os.path.abspath(__file__)])

    def show_history(self):
        """Muestra la ventana de historial"""
        if not self._history_window:
            self._history_window = HistoryWindow(self)
        self._history_window.show()
        self._history_window.raise_()
        self._history_window.activateWindow()

    def show_bookmarks(self):
        # Marcadores simples en memoria
        dialog = QDialog(self)
        dialog.setWindowTitle('Marcadores')
        dialog.setStyleSheet('background-color: #232323; color: #eee;')
        layout = QVBoxLayout(dialog)
        label = QLabel('Marcadores:')
        layout.addWidget(label)
        list_widget = QListWidget()
        for url in getattr(self, 'bookmarks', []):
            list_widget.addItem(url)
        layout.addWidget(list_widget)
        add_btn = QPushButton('Agregar marcador actual')
        add_btn.clicked.connect(lambda: self.add_bookmark(list_widget))
        layout.addWidget(add_btn)
        close_btn = QPushButton('Cerrar')
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec_()

    def add_bookmark(self, list_widget):
        url = self.current_webview().url().toString()
        if not hasattr(self, 'bookmarks'):
            self.bookmarks = []
        if url not in self.bookmarks:
            self.bookmarks.append(url)
            list_widget.addItem(url)

    def show_settings(self):
        # QLineEdit, QTabWidget, QWidget, QHBoxLayout, QRadioButton, QButtonGroup ya están importados globalmente
        dialog = QDialog(self)
        dialog.setWindowTitle('Configuración')
        dialog.setStyleSheet('background-color: #232323; color: #eee;')
        dialog.resize(600, 400)
        tabs = QTabWidget(dialog)
        tabs.setStyleSheet('background-color: #232323; color: #eee;')

        # Pestaña General
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        home_label = QLabel('Página de inicio:')
        general_layout.addWidget(home_label)
        home_edit = QLineEdit()
        home_edit.setPlaceholderText('Ejemplo: https://duckduckgo.com')
        home_edit.setText(getattr(self, 'homepage', 'https://duckduckgo.com'))
        general_layout.addWidget(home_edit)
        tabs.addTab(general_tab, 'General')

        # Pestaña Descargas
        downloads_tab = QWidget()
        downloads_layout = QVBoxLayout(downloads_tab)
        downloads_label = QLabel('Ruta de descargas predeterminada:')
        downloads_layout.addWidget(downloads_label)
        downloads_edit = QLineEdit()
        downloads_edit.setPlaceholderText('Ejemplo: /home/usuario/Descargas')
        downloads_edit.setText(getattr(self, 'download_path', os.path.expanduser('~/Descargas')))
        downloads_layout.addWidget(downloads_edit)
        browse_btn = QPushButton('Seleccionar carpeta')
        def browse_folder():
            from PyQt5.QtWidgets import QFileDialog
            folder = QFileDialog.getExistingDirectory(dialog, 'Seleccionar carpeta de descargas', downloads_edit.text())
            if folder:
                downloads_edit.setText(folder)
        browse_btn.clicked.connect(browse_folder)
        downloads_layout.addWidget(browse_btn)
        tabs.addTab(downloads_tab, 'Descargas')

        # Pestaña Contraseñas guardadas con protección por contraseña maestra
        passwords_tab = QWidget()
        passwords_layout = QVBoxLayout(passwords_tab)
        passwords_label = QLabel('Contraseñas guardadas por dominio:')
        passwords_layout.addWidget(passwords_label)
        import base64
        self.accounts = getattr(self, 'accounts', [])
        from PyQt5.QtWidgets import QInputDialog, QMessageBox
        master_key = getattr(self, 'master_password', None)
        # Opción para borrar la contraseña maestra
        delete_master_btn = QPushButton('Borrar contraseña maestra')
        def delete_master():
            self.delete_master_password()
            QMessageBox.information(dialog, 'Contraseña maestra', 'La contraseña maestra ha sido borrada.')
        delete_master_btn.clicked.connect(delete_master)
        passwords_layout.addWidget(delete_master_btn)
        # Solicitar contraseña maestra antes de mostrar la lista
        if master_key is None:
            master, ok = QInputDialog.getText(dialog, 'Establecer contraseña maestra', 'Crea una contraseña maestra:', QLineEdit.Password)
            if ok and master:
                self.master_password = master
                self.save_master_password()
            else:
                passwords_layout.addWidget(QLabel('No se estableció contraseña maestra.'))
                tabs.addTab(passwords_tab, 'Contraseñas guardadas')
                goto_next_tab = True
        else:
            pw, ok = QInputDialog.getText(dialog, 'Contraseña maestra', 'Introduce la contraseña maestra:', QLineEdit.Password)
            if not (ok and pw and pw == self.master_password):
                QMessageBox.warning(dialog, 'Acceso denegado', 'Contraseña maestra incorrecta.')
                passwords_layout.addWidget(QLabel('Acceso denegado.'))
                tabs.addTab(passwords_tab, 'Contraseñas guardadas')
                goto_next_tab = True
            else:
                goto_next_tab = False
        if not 'goto_next_tab' in locals() or not goto_next_tab:
            passwords_list = QListWidget()
            for acc in self.accounts:
                passwords_list.addItem(f"{acc['usuario']}@{acc['dominio']}")
            passwords_layout.addWidget(passwords_list)
            add_password_btn = QPushButton('Agregar contraseña')
            def add_password():
                usuario, ok1 = QInputDialog.getText(dialog, 'Agregar contraseña', 'Usuario o correo:')
                if not (ok1 and usuario):
                    return
                password, ok2 = QInputDialog.getText(dialog, 'Agregar contraseña', 'Contraseña:', QLineEdit.Password)
                if not (ok2 and password):
                    return
                dominio, ok3 = QInputDialog.getText(dialog, 'Agregar contraseña', 'Dominio (ej: gmail.com, outlook.com):')
                if not (ok3 and dominio):
                    return
                encoded = base64.b64encode(password.encode('utf-8')).decode('utf-8')
                if not any(a['usuario'] == usuario and a['dominio'] == dominio for a in self.accounts):
                    self.accounts.append({'usuario': usuario, 'password': encoded, 'dominio': dominio})
                    passwords_list.addItem(f"{usuario}@{dominio}")
                    self.save_encrypted_passwords()
            add_password_btn.clicked.connect(add_password)
            passwords_layout.addWidget(add_password_btn)
            remove_password_btn = QPushButton('Eliminar contraseña seleccionada')
            def remove_password():
                selected = passwords_list.currentRow()
                if selected >= 0:
                    item = passwords_list.item(selected).text()
                    usuario, dominio = item.split('@', 1)
                    self.accounts = [a for a in self.accounts if not (a['usuario'] == usuario and a['dominio'] == dominio)]
                    passwords_list.takeItem(selected)
                    self.save_encrypted_passwords()
            remove_password_btn.clicked.connect(remove_password)
            passwords_layout.addWidget(remove_password_btn)
            clear_data_btn = QPushButton('Borrar todas las contraseñas')
            def clear_data():
                self.accounts = []
                passwords_list.clear()
                self.save_encrypted_passwords()
            clear_data_btn.clicked.connect(clear_data)
            passwords_layout.addWidget(clear_data_btn)
        tabs.addTab(passwords_tab, 'Contraseñas guardadas')

        # Pestaña Temas
        themes_tab = QWidget()
        themes_layout = QVBoxLayout(themes_tab)
        themes_label = QLabel('Seleccionar tema:')
        themes_layout.addWidget(themes_label)
        
        themes = [
            ('Oscuro', 'theme-dark'),
            ('Azul Oscuro', 'theme-dark-blue'),
            ('Verde Oscuro', 'theme-dark-green')
        ]
        
        theme_group = QButtonGroup(themes_tab)
        for name, class_name in themes:
            btn = QRadioButton(name)
            btn.setStyleSheet('color: #eee;')
            themes_layout.addWidget(btn)
            theme_group.addButton(btn)
            # Si el tema actual coincide con este tema, seleccionarlo
            current_theme = getattr(self, 'current_theme', 'Oscuro')
            if current_theme == name:
                btn.setChecked(True)
            # Guardar el nombre de la clase CSS como propiedad del botón
            btn.theme_class = class_name
        
        # Agregar la pestaña de temas
        tabs.addTab(themes_tab, 'Temas')

        # Pestaña Proxy
        proxy_tab = QWidget()
        proxy_layout = QVBoxLayout(proxy_tab)
        proxy_label = QLabel('Configuración de proxy:')
        proxy_layout.addWidget(proxy_label)
        proxy_host = QLineEdit()
        proxy_host.setPlaceholderText('Host (ej: 127.0.0.1)')
        proxy_host.setText(getattr(self, 'proxy_host', ''))
        proxy_layout.addWidget(proxy_host)
        proxy_port = QLineEdit()
        proxy_port.setPlaceholderText('Puerto (ej: 8080)')
        proxy_port.setText(getattr(self, 'proxy_port', ''))
        proxy_layout.addWidget(proxy_port)
        remove_proxy_btn = QPushButton('Quitar proxy')
        def remove_proxy():
            proxy_host.setText("")
            proxy_port.setText("")
        remove_proxy_btn.clicked.connect(remove_proxy)
        proxy_layout.addWidget(remove_proxy_btn)
        tabs.addTab(proxy_tab, 'Proxy')

        # Layout principal
        main_layout = QVBoxLayout(dialog)
        main_layout.addWidget(tabs)

        # Botón guardar
        save_btn = QPushButton('Guardar cambios')
        def save_settings():
            self.homepage = home_edit.text() or 'https://duckduckgo.com'
            # Tema seleccionado
            checked_theme = theme_group.checkedButton()
            if checked_theme:
                old_theme = getattr(self, 'current_theme', None)
                old_theme_class = getattr(self, 'theme_class', None)
                
                try:
                    self.current_theme = checked_theme.text()
                    self.theme_class = checked_theme.theme_class
                    print(f"Cambiando de tema {old_theme} a {self.current_theme}")
                    self.apply_theme()
                except Exception as e:
                    print(f"Error al cambiar el tema: {e}")
                    # Restaurar tema anterior si hay error
                    if old_theme and old_theme_class:
                        self.current_theme = old_theme
                        self.theme_class = old_theme_class
                        self.apply_theme()
            # Proxy
            self.proxy_host = proxy_host.text()
            self.proxy_port = proxy_port.text()
            # Descargas
            self.download_path = downloads_edit.text() or os.path.expanduser('~/Descargas')
            # Sesiones
            if hasattr(self, 'session_checkboxes'):
                self.sessions = {name: cb.isChecked() for name, cb in self.session_checkboxes.items()}
            self.save_config()
            self.apply_proxy()
            dialog.accept()
        save_btn.clicked.connect(save_settings)
        main_layout.addWidget(save_btn)

        close_btn = QPushButton('Cerrar')
        close_btn.clicked.connect(dialog.accept)
        main_layout.addWidget(close_btn)
        dialog.exec_()

    def on_tab_changed(self, index):
        """Maneja el cambio de pestaña y actualiza la barra de URL"""
        if index >= 0 and index < self.tabs.count() - 1:  # Excluir el botón de nueva pestaña
            current_widget = self.tabs.widget(index)
            if hasattr(current_widget, 'url'):
                self.update_urlbar(current_widget.url())
            elif hasattr(current_widget, 'page'):
                self.update_urlbar(current_widget.page().url())

    def apply_theme(self):
        """Aplica el tema actual a toda la interfaz"""
        if not hasattr(self, 'theme_class') or not hasattr(self, 'current_theme'):
            print("No hay tema configurado")
            return
            
        print(f"Aplicando tema: {self.current_theme} ({self.theme_class})")
        
        # Definir los temas directamente en el código para asegurar su disponibilidad
        themes = {
            'theme-dark': {
                '--background': '#232323',
                '--text': '#eee',
                '--toolbar': '#2c2c2c',
                '--border': '#444',
                '--hover': '#404040',
                '--selected': '#353535',
                '--accent': '#0078d7',
                '--shadow': 'rgba(0, 0, 0, 0.3)',
                '--download-progress': '#00aa00',
                '--error': '#c42b1c',
                '--warning': '#ffd93d',
                '--tab-inactive': '#2c2c2c'
            },
            'theme-dark-blue': {
                '--background': '#1a1b26',
                '--text': '#a9b1d6',
                '--toolbar': '#24283b',
                '--border': '#414868',
                '--hover': '#2c3047',
                '--selected': '#2f354a',
                '--accent': '#7aa2f7',
                '--shadow': 'rgba(0, 0, 0, 0.4)',
                '--download-progress': '#9ece6a',
                '--error': '#f7768e',
                '--warning': '#e0af68',
                '--tab-inactive': '#1f2335'
            },
            'theme-dark-green': {
                '--background': '#1b2820',
                '--text': '#b8c4b8',
                '--toolbar': '#243229',
                '--border': '#415041',
                '--hover': '#2c3e2c',
                '--selected': '#2f432f',
                '--accent': '#6ccf7c',
                '--shadow': 'rgba(0, 0, 0, 0.4)',
                '--download-progress': '#4b9e57',
                '--error': '#cf6c6c',
                '--warning': '#cfb66c',
                '--tab-inactive': '#1f2f24'
            }
        }
        
        try:
            # Obtener las variables del tema actual
            theme_vars = themes.get(self.theme_class)
            if not theme_vars:
                raise ValueError(f"Tema no encontrado: {self.theme_class}")
            
            # Construir el CSS con las variables del tema
            css = f"""
                /* Tema: {self.current_theme} */
                QMainWindow, QDialog, QWidget {{
                    background-color: {theme_vars['--background']};
                    color: {theme_vars['--text']};
                }}
                
                QToolBar {{
                    background: {theme_vars['--toolbar']};
                    border-bottom: 1px solid {theme_vars['--border']};
                    padding: 5px;
                }}
                
                QTabWidget::pane {{
                    border: none;
                    background-color: {theme_vars['--background']};
                }}
                
                QTabBar::tab {{
                    background-color: {theme_vars['--tab-inactive']};
                    color: {theme_vars['--text']};
                    padding: 8px 25px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    min-width: 150px;
                    max-width: 200px;
                    margin-right: 2px;
                    margin-top: 5px;
                }}
                
                QTabBar::tab:hover {{
                    background-color: {theme_vars['--hover']};
                }}
                
                QTabBar::tab:selected {{
                    background-color: {theme_vars['--selected']};
                }}
                
                QLineEdit {{
                    background-color: {theme_vars['--toolbar']};
                    color: {theme_vars['--text']};
                    border: 1px solid {theme_vars['--border']};
                    padding: 5px;
                    border-radius: 4px;
                }}
                
                QPushButton {{
                    background-color: {theme_vars['--toolbar']};
                    color: {theme_vars['--text']};
                    border: 1px solid {theme_vars['--border']};
                    padding: 5px 10px;
                    border-radius: 3px;
                }}
                
                QPushButton:hover {{
                    background-color: {theme_vars['--hover']};
                    border-color: {theme_vars['--accent']};
                }}
                
                QListWidget {{
                    background-color: {theme_vars['--toolbar']};
                    color: {theme_vars['--text']};
                    border: 1px solid {theme_vars['--border']};
                }}
                
                QListWidget::item:hover {{
                    background-color: {theme_vars['--hover']};
                }}
                
                QMenu {{
                    background-color: {theme_vars['--background']};
                    color: {theme_vars['--text']};
                    border: 1px solid {theme_vars['--border']};
                }}
                
                QMenu::item:selected {{
                    background-color: {theme_vars['--hover']};
                }}
                
                QProgressBar {{
                    border: 1px solid {theme_vars['--border']};
                    background-color: {theme_vars['--toolbar']};
                    color: {theme_vars['--text']};
                }}
                
                QProgressBar::chunk {{
                    background-color: {theme_vars['--download-progress']};
                }}
            """
            
            # Aplicar el estilo a la ventana principal
            self.setStyleSheet(css)
            
            # Aplicar el estilo a todas las ventanas existentes
            for window in [
                self._history_window,
                self._downloads_window,
                getattr(self, 'suggest_popup', None)
            ]:
                if window:
                    window.setStyleSheet(css)
            
            # Aplicar tema a las pestañas del navegador
            if hasattr(self, 'tabs'):
                for i in range(self.tabs.count() - 1):
                    browser = self.tabs.widget(i)
                    if isinstance(browser, QWebEngineView):
                        is_dark = 'dark' in self.theme_class
                        browser.page().runJavaScript(f'''
                            document.documentElement.style.setProperty('color-scheme', 
                                '{is_dark and "dark" or "light"}');
                        ''')
            
            print("Tema aplicado exitosamente")
            
        except Exception as e:
            print(f"Error al aplicar el tema: {e}")
            # Aplicar tema oscuro por defecto
            self.current_theme = 'Oscuro'
            self.theme_class = 'theme-dark'
            self.apply_theme()

    def apply_theme_to_widget(self, widget):
        """Aplica el tema actual a un widget específico"""
        if not hasattr(self, 'theme_class') or not widget:
            return
        
        try:
            # Agregar el widget a la lista de ventanas si no está
            if hasattr(widget, 'show') and widget not in self._windows:
                self._windows.append(widget)
                
            # Obtener el estilo actual de la ventana principal
            style = self.styleSheet()
            if style:
                widget.setStyleSheet(style)
                # Aplicar también a los widgets hijos
                for child in widget.findChildren(QWidget):
                    child.setStyleSheet(style)
                    
        except Exception as e:
            print(f"Error al aplicar tema al widget: {e}")

    def apply_proxy(self):
        # Aplicar configuración de proxy (requiere reiniciar la aplicación)
        pass

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Acerca de')
        dialog.setStyleSheet('background-color: #232323; color: #eee;')
        layout = QVBoxLayout(dialog)
        label = QLabel('Fennex Browser estilo moderno\nDesarrollado por B&R.Comp')
        layout.addWidget(label)
        close_btn = QPushButton('Cerrar')
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        dialog.exec_()

    def update_urlbar(self, qurl=None, browser=None):
        # Si el primer parámetro es un entero (índice de pestaña), no hacer nada
        if isinstance(qurl, int):
            return
            
        if browser and browser != self.current_webview():
            return
            
        # Guardar historial
        if not hasattr(self, 'history'):
            self.history = []
            
        if qurl is None:
            qurl = self.current_webview().url()
            
        # Verificar que qurl es un QUrl válido
        if hasattr(qurl, 'toString'):
            url_str = qurl.toString()
            if url_str and (not self.history or self.history[-1] != url_str):
                self.history.append(url_str)
            self.urlbar.setText(url_str)
            self.urlbar.setCursorPosition(0)

    def add_new_tab(self, qurl=None, label='Nueva pestaña'):
        if qurl is None:
            qurl = QUrl('https://duckduckgo.com/')
            
        # Crear un nuevo QWebEngineView
        browser = QWebEngineView()
        
        # Usar el perfil global para todas las pestañas
        from PyQt5.QtWebEngineWidgets import QWebEngineProfile, QWebEnginePage
        profile = QWebEngineProfile.defaultProfile()
        page = QWebEnginePage(profile, browser)
        browser.setPage(page)
        
        # Conectar la señal de cambio de título
        browser.titleChanged.connect(lambda title: self.update_tab_title(browser, title))
        
        # Configurar el perfil
        profile.setHttpUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36')
        profile.setHttpAcceptLanguage('es-ES,es;q=0.9,en;q=0.8')
        
        # Habilitar plugins y JavaScript
        settings = browser.settings()
        settings.setAttribute(settings.PluginsEnabled, True)
        settings.setAttribute(settings.JavascriptEnabled, True)
        settings.setAttribute(settings.JavascriptCanOpenWindows, True)
        settings.setAttribute(settings.AllowRunningInsecureContent, True)
        settings.setAttribute(settings.LocalStorageEnabled, True)
        settings.setAttribute(settings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.AllowGeolocationOnInsecureOrigins, True)
        settings.setAttribute(settings.AllowWindowActivationFromJavaScript, True)
        
        # Configurar política de seguridad de contenido más permisiva
        page = browser.page()
        
        # Configurar permisos de características
        def permission_handler(origin, feature):
            return page.PermissionGrantedByUser
        page.featurePermissionRequested.connect(
            lambda origin, feature: page.setFeaturePermission(origin, feature, permission_handler(origin, feature))
        )
        
        # Establecer CSP más permisiva
        page.profile().setUrlRequestInterceptor(None)  # Deshabilitar interceptor de solicitudes
        
        # Configurar manejador de mensajes de consola JavaScript
        def ignore_js_console(level, message, line, source):
            pass
        page.javaScriptConsoleMessage = ignore_js_console
        
        # Configurar permisos adicionales
        page.profile().setPersistentCookiesPolicy(page.profile().AllowPersistentCookies)
        page.profile().setHttpCacheType(page.profile().MemoryHttpCache)
        
        # Establecer la URL
        browser.setUrl(qurl)
        
        # Conectar señales
        # Conectar señales para credenciales
        browser.loadFinished.connect(lambda ok, browser=browser: self.inject_credentials(browser.url()))
        browser.loadFinished.connect(lambda ok, browser=browser: self.prompt_save_credentials(browser))
        
        # Conectar señales para historial
        def update_history(ok, browser=browser):
            if ok and browser.url().scheme() in ['http', 'https']:
                self.add_to_history(browser.url(), browser.title())
        browser.loadFinished.connect(update_history)
        
        # Conectar señal para actualizar la barra de URL
        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        
        # Insertar antes de la pestaña de nueva pestaña
        i = self.tabs.insertTab(self.tabs.count() - 1, browser, label)
        self.tabs.setCurrentIndex(i)

    def on_download_requested(self, download):
        """Maneja las solicitudes de descarga"""
        print(f"Solicitud de descarga recibida: {download.downloadFileName()}")
        
        # Obtener el nombre sugerido del archivo
        suggested_filename = download.downloadFileName()
        if not suggested_filename:
            suggested_filename = "download"
            
        # Crear un diálogo de selección de archivo
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        
        # Mostrar diálogo de confirmación con detalles del archivo
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle('Confirmar descarga')
        
        # Preparar información del archivo
        file_size = download.totalBytes()
        size_str = "Desconocido"
        if file_size > 0:
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size/1024:.1f} KB"
            else:
                size_str = f"{file_size/(1024*1024):.1f} MB"
                
        msg.setText(f'¿Deseas descargar este archivo?\n\n'
                   f'Nombre: {suggested_filename}\n'
                   f'Tamaño: {size_str}\n'
                   f'Desde: {download.url().toString()}')
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        
        if msg.exec_() != QMessageBox.Yes:
            download.cancel()
            return
            
        # Mostrar diálogo para seleccionar ubicación
        full_path, _ = QFileDialog.getSaveFileName(
            self,
            'Guardar archivo',
            os.path.join(self.download_path, suggested_filename),
            'Todos los archivos (*.*)'
        )
        
        # Si el usuario cancela el diálogo
        if not full_path:
            download.cancel()
            return
            
        # Actualizar la ruta de descarga predeterminada
        self.download_path = os.path.dirname(full_path)
        
        print(f"Iniciando descarga en: {full_path}")
        
        try:
            # Asegurarse de que la carpeta de destino exista
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Configurar la descarga
            download.setPath(full_path)
            
            # Mostrar la ventana de descargas
            if self._downloads_window is None:
                self._downloads_window = DownloadsWindow(self)
            
            self._downloads_window.show()
            self._downloads_window.raise_()
            self._downloads_window.activateWindow()
            
            # Agregar la descarga a la ventana antes de iniciarla
            self._downloads_window.add_download(download)
            
            # Iniciar la descarga
            download.accept()
            print(f"Descarga aceptada: {full_path}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                'Error de descarga',
                f'No se pudo iniciar la descarga:\n{str(e)}'
            )
            download.cancel()
            print(f"Error al iniciar la descarga: {e}")

    def add_blank_tab(self):
        self.add_new_tab(QUrl('https://duckduckgo.com/'), 'Nueva pestaña')

    def close_tab(self, i):
        # Evita cerrar el botón de nueva pestaña
        if i == self.tabs.count() - 1:
            return
        if self.tabs.count() > 2:  # Al menos una pestaña normal y el botón de nueva pestaña
            self.tabs.removeTab(i)
            # Si la pestaña seleccionada es el botón de nueva pestaña, selecciona la anterior
            if self.tabs.currentIndex() == self.tabs.count() - 1:
                self.tabs.setCurrentIndex(self.tabs.count() - 2)

    def update_tab_title(self, browser, title):
        """Actualiza el título de la pestaña con el título de la página"""
        index = self.tabs.indexOf(browser)
        if index != -1:  # Si se encuentra la pestaña
            # Si el título está vacío, usa 'Nueva pestaña'
            if not title:
                title = 'Nueva pestaña'
            # Truncar el título si es muy largo (máximo 20 caracteres)
            if len(title) > 20:
                title = title[:17] + '...'
            self.tabs.setTabText(index, title)

    def current_webview(self):
        return self.tabs.currentWidget()

    def navigate_to_url(self):
        text = self.urlbar.text().strip()
        # Si parece URL, navega directo; si no, busca en DuckDuckGo
        if text.startswith('http://') or text.startswith('https://') or '.' in text:
            q = QUrl(text)
            if q.scheme() == '':
                q.setScheme('http')
            self.current_webview().setUrl(q)
        else:
            # Buscar en DuckDuckGo
            search_url = f'https://duckduckgo.com/?q={text}'
            self.current_webview().setUrl(QUrl(search_url))

    def navigate_home(self):
        self.current_webview().setUrl(QUrl('https://duckduckgo.com'))

    def add_bookmark(self):
        # Obtiene la URL y título de la página actual
        url = self.current_webview().url().toString()
        title = self.current_webview().page().title()

        # Verifica si el marcador ya existe
        if not hasattr(self, 'bookmarks'):
            self.bookmarks = []

        # Si el marcador ya existe, muestra un mensaje
        if any(b.get('url') == url for b in self.bookmarks):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, 'Marcador', 'Esta página ya está en marcadores')
            return

        # Agrega el nuevo marcador
        self.bookmarks.append({
            'title': title,
            'url': url
        })

        # Guarda los marcadores en un archivo
        self.save_bookmarks()

        # Muestra un mensaje de confirmación
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(self, 'Marcador', 'Página agregada a marcadores')

    def save_bookmarks(self):
        # Guarda los marcadores en un archivo JSON
        import json
        bookmarks_file = os.path.expanduser('~/.pyqt_chrome_bookmarks.json')
        try:
            with open(bookmarks_file, 'w') as f:
                json.dump({'bookmarks': self.bookmarks}, f)
        except Exception:
            pass

    def load_bookmarks(self):
        # Carga los marcadores desde el archivo JSON
        import json
        bookmarks_file = os.path.expanduser('~/.pyqt_chrome_bookmarks.json')
        self.bookmarks = []
        if os.path.exists(bookmarks_file):
            try:
                with open(bookmarks_file, 'r') as f:
                    data = json.load(f)
                    self.bookmarks = data.get('bookmarks', [])
            except Exception:
                pass

    def translate_page(self):
        import urllib.parse
        # Obtiene la URL actual
        current_url = self.current_webview().url().toString()
        
        # Si ya es una URL de Google Translate, obtén la URL original
        if 'translate.google.com' in current_url:
            try:
                original_url = urllib.parse.parse_qs(urllib.parse.urlparse(current_url).query)['u'][0]
                self.current_webview().setUrl(QUrl(original_url))
                return
            except:
                pass
        
        # Si no es una URL de Google Translate, traduce la página
        translate_url = f'https://translate.google.com/translate?sl=auto&tl=es&u={urllib.parse.quote(current_url)}'
        self.current_webview().setUrl(QUrl(translate_url))

    def install_current_pwa(self):
        """Instala la PWA detectada creando un acceso directo .desktop"""
        current_tab = self.current_webview().parent()
        if not current_tab or not hasattr(current_tab, "current_manifest") or not current_tab.current_manifest:
            print("[ERROR] No hay PWA para instalar")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Error",
                "Esta página web no se puede instalar como aplicación.\nAsegúrate de que el sitio soporte PWAs."
            )
            return

        manifest = current_tab.current_manifest
        name = manifest.get("name", "PWA")
        url = manifest.get("start_url", manifest.get("currentUrl", self.current_webview().url().toString()))
        icon = None

        # Si la PWA tiene iconos, usar el más grande
        icons = manifest.get("icons", [])
        if icons:
            # Ordenar por tamaño (si está disponible)
            icons.sort(
                key=lambda i: int(str(i.get("sizes", "0x0")).split("x")[0]),
                reverse=True
            )
            icon = icons[0].get("src")
            
            # Si la URL del ícono es relativa, convertirla a absoluta
            if icon and not icon.startswith(('http://', 'https://')):
                from urllib.parse import urljoin
                icon = urljoin(url, icon)

        # Crear un ID único para la PWA basado en la URL
        pwa_id = "foxpy." + hashlib.md5(url.encode()).hexdigest()[:8]

        # Crear directorio para aplicaciones instaladas si no existe
        apps_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(apps_dir, exist_ok=True)

        # Preparar el archivo .desktop con metadatos adicionales
        desktop_entry = f"""[Desktop Entry]
    Name={name}
    Comment=Aplicación web: {manifest.get('description', name)}
    Exec=python3 {os.path.abspath(__file__)} --app="{url}"
    Icon={icon if icon else "web-browser"}
    Type=Application
    Categories=Network;WebBrowser;
    Terminal=false
    StartupWMClass={pwa_id}
    """
        # Guardar el archivo .desktop
        filepath = os.path.join(apps_dir, f"{pwa_id}.desktop")

        try:
            with open(filepath, "w") as f:
                f.write(desktop_entry)
            os.chmod(filepath, 0o755)
            print(f"[INFO] PWA instalada: {filepath}")

            # Mostrar mensaje de éxito
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "PWA Instalada",
                f'La aplicación "{name}" se ha instalado correctamente.\nLa encontrarás en tu menú de aplicaciones.'
            )

        except Exception as e:
            print(f"[ERROR] No se pudo instalar la PWA: {e}")
            QMessageBox.critical(
                self,
                "Error",
                "Esta página web no se puede instalar como aplicación.\n"
                "Asegúrate de que el sitio soporte PWAs."
            )
            return

        manifest = current_tab.current_manifest
        print("[INFO] Instalando PWA:", manifest)

        # Obtener datos relevantes del manifest
        name = manifest.get('name', 'PWA')
        short_name = manifest.get('short_name', name)
        description = manifest.get('description', '')
        start_url = manifest.get('start_url', '') or manifest.get('currentUrl', current_tab.url().toString())
        icon_list = manifest.get('icons', [])
        
        # Crear diálogo de confirmación personalizado con tema oscuro
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
        dialog = QDialog(self)
        dialog.setWindowTitle('Instalar aplicación web')
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #232323;
                color: #eee;
            }
            QLabel {
                color: #eee;
                margin-bottom: 5px;
            }
            QLabel#title {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
            }
            QLabel#description {
                color: #bbb;
                margin-bottom: 15px;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton#install {
                background-color: #0078d4;
                border: none;
                color: white;
            }
            QPushButton#install:hover {
                background-color: #0086ef;
            }
            QPushButton#cancel {
                background-color: #333;
                border: 1px solid #444;
                color: #eee;
            }
            QPushButton#cancel:hover {
                background-color: #444;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título de la instalación
        title_label = QLabel(f"¿Instalar {name}?")
        title_label.setObjectName("title")
        layout.addWidget(title_label)

        # Descripción de la aplicación
        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("description")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Detalles técnicos y características
        details = []
        if manifest.get('display'):
            details.append(f"• Modo de visualización: {manifest['display']}")
        if start_url:
            details.append(f"• URL inicial: {start_url}")
        if manifest.get('theme_color'):
            details.append(f"• Color del tema: {manifest['theme_color']}")
        
        if details:
            details_label = QLabel("\n".join(details))
            details_label.setWordWrap(True)
            layout.addWidget(details_label)

        # Sección de permisos
        perms_label = QLabel("\nEsta aplicación tendrá acceso a:")
        perms_label.setStyleSheet("color: #bbb; margin-top: 10px;")
        layout.addWidget(perms_label)
        
        permissions = [
            "• Almacenamiento local para datos offline",
            "• Caché del navegador",
            "• Cookies y datos del sitio"
        ]
        
        if manifest.get('permissions'):
            for perm in manifest['permissions']:
                permissions.append(f"• {perm}")
        
        perms_details = QLabel("\n".join(permissions))
        perms_details.setStyleSheet("color: #bbb;")
        perms_details.setWordWrap(True)
        layout.addWidget(perms_details)

        # Botones de acción
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        install_btn = QPushButton("Instalar")
        install_btn.setObjectName("install")
        install_btn.clicked.connect(dialog.accept)
        install_btn.setDefault(True)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(install_btn)
        layout.addLayout(button_layout)

        # Si el usuario cancela, salir
        if dialog.exec_() != QDialog.Accepted:
            print("[INFO] Instalación cancelada por el usuario")
            return

        try:
            # Crear directorios necesarios
            apps_dir = os.path.expanduser("~/.local/share/applications")
            icons_dir = os.path.expanduser("~/.local/share/icons/hicolor")
            os.makedirs(apps_dir, exist_ok=True)
            os.makedirs(icons_dir, exist_ok=True)

            # Generar ID único para la PWA
            pwa_id = "foxpy." + hashlib.md5(start_url.encode()).hexdigest()[:8]

            # Procesar y guardar el ícono
            icon_path = "web-browser"  # Ícono por defecto
            if icon_list:
                try:
                    # Ordenar íconos por tamaño (preferir el más grande)
                    icons_by_size = sorted(
                        icon_list,
                        key=lambda i: int(str(i.get('sizes', '0x0')).split('x')[0]),
                        reverse=True
                    )
                    
                    best_icon = icons_by_size[0]
                    icon_url = best_icon.get('src', '')
                    
                    # Convertir URL relativa a absoluta si es necesario
                    if icon_url and not icon_url.startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        icon_url = urljoin(start_url, icon_url)
                    
                    if icon_url:
                        # Determinar el tamaño del ícono
                        icon_size = best_icon.get('sizes', '128x128').split('x')[0]
                        icon_dir = os.path.join(icons_dir, f"{icon_size}x{icon_size}")
                        os.makedirs(icon_dir, exist_ok=True)
                        
                        # Procesar nombre y extensión del ícono
                        from urllib.parse import urlparse
                        from os.path import splitext
                        icon_ext = splitext(urlparse(icon_url).path)[1] or '.png'
                        icon_filename = f"{pwa_id}{icon_ext}"
                        icon_save_path = os.path.join(icon_dir, icon_filename)
                        
                        # Descargar y guardar el ícono
                        import requests
                        response = requests.get(icon_url, timeout=5)
                        response.raise_for_status()
                        
                        with open(icon_save_path, 'wb') as f:
                            f.write(response.content)
                        
                        # Actualizar la ruta del ícono
                        icon_path = os.path.splitext(icon_filename)[0]
                        print(f"[INFO] Ícono guardado: {icon_save_path}")

                except Exception as e:
                    print(f"[ERROR] Error al procesar el ícono: {e}")
                    # Continuar con el ícono por defecto
            
            # Crear archivo .desktop
            desktop_entry = f"""[Desktop Entry]
Name={name}
Comment=Web App for {short_name}
Exec=python3 {os.path.abspath(__file__)} --app="{start_url}"
Icon={icon_path}
Type=Application
Categories=Network;WebBrowser;
StartupWMClass={pwa_id}
"""

            # Guardar el archivo .desktop
            desktop_file = os.path.join(apps_dir, f"{pwa_id}.desktop")
            try:
                with open(desktop_file, "w") as f:
                    f.write(desktop_entry)
                os.chmod(desktop_file, 0o755)
                print(f"[INFO] PWA instalada en: {desktop_file}")

                # Mostrar mensaje de éxito
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(
                    self,
                    'PWA Instalada',
                    f'La aplicación {name} ha sido instalada correctamente.\n'
                    'Puedes encontrarla en tu menú de aplicaciones.'
                )

            except Exception as e:
                print(f"[ERROR] Error al guardar el archivo .desktop: {e}")
                QMessageBox.critical(
                    self,
                    'Error',
                    f'Error al instalar la PWA:\n{str(e)}'
                )
                
        except Exception as e:
            print(f"[ERROR] Error general en la instalación: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                'Error',
                f'Error al instalar la PWA:\n{str(e)}'
            )


    def show_bookmarks(self):
        # Crea un diálogo para mostrar los marcadores
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QPushButton, 
                                   QHBoxLayout, QFileDialog, QMessageBox)
        from datetime import datetime
        import html

        dialog = QDialog(self)
        dialog.setWindowTitle('Marcadores')
        dialog.setStyleSheet('background-color: #232323; color: #eee;')
        layout = QVBoxLayout(dialog)

        # Lista de marcadores
        bookmarks_list = QListWidget()
        bookmarks_list.setStyleSheet('''
            QListWidget {
                background-color: #2c2c2c;
                color: #eee;
                border: 1px solid #444;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
        ''')

        def refresh_bookmarks_list():
            bookmarks_list.clear()
            for bookmark in self.bookmarks:
                bookmarks_list.addItem(f"{bookmark['title']} - {bookmark['url']}")

        # Agrega los marcadores a la lista
        refresh_bookmarks_list()

        # Doble clic en un marcador abre la URL
        def open_bookmark(item):
            # Obtiene la URL del texto del item (después del guión)
            url = item.text().split(' - ')[1]
            self.current_webview().setUrl(QUrl(url))
            dialog.accept()
        bookmarks_list.itemDoubleClicked.connect(open_bookmark)

        layout.addWidget(bookmarks_list)

        # Función para exportar marcadores
        def export_bookmarks():
            file_path, _ = QFileDialog.getSaveFileName(
                dialog,
                'Exportar Marcadores',
                os.path.expanduser('~/Marcadores.html'),
                'Archivos HTML (*.html);;Todos los archivos (*.*)'
            )
            if not file_path:
                return

            try:
                html_content = '''<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file.
     It will be read and overwritten.
     DO NOT EDIT! -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Marcadores</TITLE>
<H1>Marcadores</H1>
<DL><p>
'''
                for bookmark in self.bookmarks:
                    date_added = datetime.now().timestamp()
                    html_content += f'''    <DT><A HREF="{html.escape(bookmark['url'])}" ADD_DATE="{int(date_added)}">{html.escape(bookmark['title'])}</A>\n'''
                
                html_content += '</DL><p>\n'

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                QMessageBox.information(dialog, 'Éxito', 'Marcadores exportados correctamente')
            except Exception as e:
                QMessageBox.critical(dialog, 'Error', f'Error al exportar marcadores: {str(e)}')

        # Función para importar marcadores
        def import_bookmarks():
            file_path, _ = QFileDialog.getOpenFileName(
                dialog,
                'Importar Marcadores',
                os.path.expanduser('~'),
                'Archivos HTML (*.html);;Todos los archivos (*.*)'
            )
            if not file_path:
                return

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                import re
                # Buscar todos los enlaces en el archivo HTML
                pattern = r'<A[^>]+HREF="([^"]+)"[^>]*>([^<]+)</A>'
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                imported = 0
                for match in matches:
                    url = html.unescape(match.group(1))
                    title = html.unescape(match.group(2))
                    
                    # Verificar si el marcador ya existe
                    if not any(b['url'] == url for b in self.bookmarks):
                        self.bookmarks.append({'url': url, 'title': title})
                        imported += 1
                
                if imported > 0:
                    self.save_bookmarks()
                    refresh_bookmarks_list()
                    QMessageBox.information(
                        dialog, 
                        'Éxito', 
                        f'Se importaron {imported} marcadores nuevos'
                    )
                else:
                    QMessageBox.information(
                        dialog,
                        'Información',
                        'No se encontraron marcadores nuevos para importar'
                    )
            except Exception as e:
                QMessageBox.critical(dialog, 'Error', f'Error al importar marcadores: {str(e)}')

        # Botones
        button_layout = QHBoxLayout()

        # Botón de importar
        import_btn = QPushButton('Importar')
        import_btn.clicked.connect(import_bookmarks)
        button_layout.addWidget(import_btn)

        # Botón de exportar
        export_btn = QPushButton('Exportar')
        export_btn.clicked.connect(export_bookmarks)
        button_layout.addWidget(export_btn)

        delete_btn = QPushButton('Eliminar')
        def delete_bookmark():
            current_row = bookmarks_list.currentRow()
            if current_row >= 0:
                # Elimina el marcador de la lista y del arreglo
                self.bookmarks.pop(current_row)
                bookmarks_list.takeItem(current_row)
                self.save_bookmarks()
        delete_btn.clicked.connect(delete_bookmark)
        button_layout.addWidget(delete_btn)

        close_btn = QPushButton('Cerrar')
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        dialog.exec_()

if __name__ == '__main__':
    import os, json
    import argparse

    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='FoxPy Browser')
    parser.add_argument('--app', type=str, help='URL de la aplicación web a cargar en modo PWA')
    args = parser.parse_args()

    def get_proxy_env():
        config_file = os.path.expanduser('~/.pyqt_chrome_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                host = config.get('proxy_host', '')
                port = config.get('proxy_port', '')
                if host and port:
                    return f'http://{host}:{port}'
            except Exception:
                pass
        return ''

    proxy_url = get_proxy_env()
    if proxy_url:
        os.environ['QTWEBENGINE_HTTP_PROXY'] = proxy_url

    app = QApplication(sys.argv)
    
    # Si se especifica --app, iniciar en modo PWA
    if args.app:
        # Crear una ventana simple para la PWA
        window = QMainWindow()
        window.setWindowTitle('Aplicación Web')
        window.setMinimumSize(800, 600)
        
        # Crear vista web sin controles
        webview = QWebEngineView()
        window.setCentralWidget(webview)
        
        # Cargar la URL
        webview.setUrl(QUrl(args.app))
        
        # Aplicar estilo sin bordes y configuración para PWA
        window.setWindowFlags(Qt.Window)
        window.setAttribute(Qt.WA_DeleteOnClose)
        
        # Mostrar la ventana
        window.show()
    else:
        # Modo navegador normal
        window = MainWindow()
        window.show()
        def on_close():
            window.save_config()
        app.aboutToQuit.connect(on_close)
    
    sys.exit(app.exec_())