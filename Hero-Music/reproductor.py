from PyQt5.QtCore import QSettings, QEvent, Qt, QTimer, QSize, pyqtSignal, QUrl
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QSlider, 
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QDialog, QMenu, QWidgetAction,
    QSizePolicy, QTabWidget, QWidget, QComboBox, QCheckBox,
    QSystemTrayIcon
)
from PyQt5.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPixmap
import os
import sys
import pygame
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
import json

# Modificar las funciones de guardado y carga
def save_window_state(window_name, geometry, state):
    """Guarda el estado de la ventana en setting.json"""
    # Obtener la ruta absoluta del directorio del script
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(config_dir, 'setting.json')
    
    config = {}
    
    # Cargar configuración existente si existe
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            # Si el archivo está corrupto, empezar con un diccionario vacío
            config = {}
    
    # Guardar nueva configuración
    config[window_name] = {
        'x': geometry.x(),
        'y': geometry.y(),
        'width': geometry.width(),
        'height': geometry.height(),
        'state': int(state)
    }
    
    # Escribir al archivo asegurándose que el directorio existe
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuración guardada en: {config_file}")  # Debug
    except Exception as e:
        print(f"Error al guardar la configuración: {e}")  # Debug

def load_window_state(window_name, default_geometry):
    """Carga el estado de la ventana desde setting.json"""
    # Obtener la ruta absoluta del directorio del script
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(config_dir, 'setting.json')
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                if window_name in config:
                    print(f"Configuración cargada para: {window_name}")  # Debug
                    return config[window_name]
    except Exception as e:
        print(f"Error al cargar la configuración: {e}")  # Debug
    
    print(f"Usando configuración por defecto para: {window_name}")  # Debug
    return {
        'x': default_geometry[0],
        'y': default_geometry[1],
        'width': default_geometry[2],
        'height': default_geometry[3],
        'state': 0
    }

def load_stylesheet():
    """Carga el archivo CSS del tema oscuro"""
    style_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dark_theme.css')
    try:
        with open(style_file, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error al cargar el tema: {e}")
        return ""

def get_icon_path():
    """Obtiene la ruta absoluta del ícono"""
    # Intenta diferentes ubicaciones posibles
    possible_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons', 'icon.png'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icons', 'icon.png'),
        os.path.abspath(os.path.join('icons', 'icon.png')),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Ícono encontrado en: {path}")  # Debug
            return path
            
    print("No se encontró el archivo icon.png en ninguna ubicación")  # Debug
    return None

class PlaylistWindow(QWidget):
    play_signal = pyqtSignal(str)
    add_file_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        
        # Establecer el título de la ventana
        self.setWindowTitle("Lista de reproducción")  # Añadir esta línea
    
        # Establecer el icono de la ventana
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        
        # Definir atributos de la clase primero
        self.btn_add = QPushButton()
        self.btn_up = QPushButton()
        self.btn_down = QPushButton()
        self.btn_remove = QPushButton()
        self.playlist = QListWidget()
        
        self.init_ui()  # Primero inicializamos la UI
        self.load_saved_geometry()  # Luego cargamos la geometría

    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        # Configurar tamaño de botones
        button_size = 24
        icon_size = 16
        
        # Configurar botones con iconos
        self.btn_add.setIcon(QIcon.fromTheme('list-add'))
        self.btn_add.setToolTip('Agregar audio')
        self.btn_add.clicked.connect(self.add_audio)
        
        self.btn_up.setIcon(QIcon.fromTheme('go-up'))
        self.btn_up.setToolTip('Mover arriba')
        self.btn_up.clicked.connect(self.move_up)
        
        self.btn_down.setIcon(QIcon.fromTheme('go-down'))
        self.btn_down.setToolTip('Mover abajo')
        self.btn_down.clicked.connect(self.move_down)
        
        self.btn_remove.setIcon(QIcon.fromTheme('list-remove'))
        self.btn_remove.setToolTip('Eliminar audio')
        self.btn_remove.clicked.connect(self.remove_audio)
        
        # Configurar tamaño de botones (sin estilos individuales)
        for button in [self.btn_add, self.btn_up, self.btn_down, self.btn_remove]:
            button.setFixedSize(button_size, button_size)
            button.setIconSize(QSize(icon_size, icon_size))
    
        # Configurar lista
        self.playlist.setDragDropMode(QListWidget.InternalMove)
        self.playlist.setDefaultDropAction(Qt.MoveAction)
        self.playlist.itemDoubleClicked.connect(self.play_item)
        
        # Crear layout de botones
        button_layout = QHBoxLayout()
        for button in [self.btn_add, self.btn_up, self.btn_down, self.btn_remove]:
            button_layout.addWidget(button)
        button_layout.addStretch()
        
        # Layout principal
        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.playlist)
        self.setLayout(layout)
        
        # Habilitar drops
        self.setAcceptDrops(True)
        
        # Aplicar estilo a la ventana
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)

    def load_saved_geometry(self):
        """Carga la geometría guardada del archivo JSON"""
        try:
            state = load_window_state('playlist', (200, 200, 300, 400))
            self.setGeometry(state['x'], state['y'], state['width'], state['height'])
            if state['state']:
                self.setWindowState(Qt.WindowState(state['state']))
        except Exception as e:
            print(f"Error al cargar geometría: {e}")

        # Configurar tamaño de botones
        button_size = 24
        icon_size = 16
        for button in [self.btn_add, self.btn_up, self.btn_down, self.btn_remove]:
            button.setFixedSize(button_size, button_size)
            button.setIconSize(QSize(icon_size, icon_size))
            # Eliminar el setStyleSheet individual de los botones

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Acepta el arrastre solo si son archivos externos"""
        if event.source() is None and event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Procesa los archivos soltados"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            if file_path.lower().endswith(('.mp3', '.wav')):
                self.add_file_signal.emit(file_path)

    def play_item(self, item):
        """Emite la señal para reproducir el archivo seleccionado"""
        index = self.playlist.row(item)
        self.play_signal.emit(str(index))

    def add_audio(self):
        """Abre diálogo para seleccionar archivo"""
        filename, _ = QFileDialog.getOpenFileName(
            self, 
            "Selecciona un archivo de audio", 
            "", 
            "Audio Files (*.mp3 *.wav)"
        )
        if filename:
            self.add_file_signal.emit(filename)

    def move_up(self):
        current = self.playlist.currentRow()
        if current > 0:
            item = self.playlist.takeItem(current)
            self.playlist.insertItem(current - 1, item)
            self.playlist.setCurrentRow(current - 1)
            if isinstance(self.parent(), AudioPlayer):
                self.parent().sync_playlist_with_widget()

    def move_down(self):
        current = self.playlist.currentRow()
        if current < self.playlist.count() - 1:
            item = self.playlist.takeItem(current)
            self.playlist.insertItem(current + 1, item)
            self.playlist.setCurrentRow(current + 1)
            if isinstance(self.parent(), AudioPlayer):
                self.parent().sync_playlist_with_widget()

    def remove_audio(self):
        current = self.playlist.currentRow()
        if current >= 0:
            self.playlist.takeItem(current)
            if isinstance(self.parent(), AudioPlayer):
                self.parent().sync_playlist_with_widget()

    def closeEvent(self, event):
        """Guardar geometría y estado al cerrar"""
        save_window_state('playlist', self.geometry(), self.windowState())
        event.accept()

    def sync_playlist_with_widget(self):
        """Sincroniza la lista interna con el orden visual del QListWidget."""
        new_playlist = []
        for i in range(self.playlist_window.playlist.count()):
            item = self.playlist_window.playlist.item(i)
            new_playlist.append(item.toolTip())  # Obtiene la ruta completa del archivo
        self.playlist = new_playlist  # Actualiza la lista interna

class AudioPlayer(QWidget):
    def __init__(self):
        super().__init__()
        
        # Establecer el título de la ventana
        self.setWindowTitle("Hero Music Player")  # Añadir esta línea
    
        # Inicializar pygame.mixer al inicio
        try:
            pygame.mixer.init()
        except pygame.error:
            QMessageBox.warning(self, "Error", "No se pudo inicializar el sistema de audio")
        
        self.settings = QSettings('Player', 'AudioPlayer')
        
        # Crear el tray icon primero
        self.tray_icon = QSystemTrayIcon(self)
        
        # Obtener la ruta del ícono
        icon_path = get_icon_path()
        if icon_path:
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            self.tray_icon.setIcon(icon)
        else:
            self.setWindowIcon(QIcon.fromTheme('audio-x-generic'))
            self.tray_icon.setIcon(QIcon.fromTheme('audio-x-generic'))
        
        # Conectar la señal activated del tray icon
        self.tray_icon.activated.connect(self.activateFromTray)
        
        # Crear menú para el icono
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Mostrar")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Salir")
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Definir tamaños de botones e iconos al inicio
        button_size = 24
        icon_size = 16

        # Crear el label primero
        self.label = QLabel("No hay archivo cargado")
        self.label.setTextFormat(Qt.PlainText)
        self.label.setWordWrap(False)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setMinimumWidth(200)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Crear los botones
        self.btn_load = QPushButton()
        self.btn_load.setIcon(QIcon.fromTheme('folder-open'))
        self.btn_load.setToolTip('Cargar archivo')
        
        self.btn_play = QPushButton()
        self.btn_play.setIcon(QIcon.fromTheme('media-playback-start'))
        self.btn_play.setEnabled(False)
        
        self.btn_pause = QPushButton()
        self.btn_pause.setIcon(QIcon.fromTheme('media-playback-pause'))
        self.btn_pause.setEnabled(False)
        
        self.btn_stop = QPushButton()
        self.btn_stop.setIcon(QIcon.fromTheme('media-playback-stop'))
        self.btn_stop.setEnabled(False)
        
        self.btn_playlist = QPushButton()
        self.btn_playlist.setIcon(QIcon.fromTheme('view-list'))
        
        self.volume_button = QPushButton()
        self.volume_button.setIcon(QIcon.fromTheme('audio-volume-high'))
        self.volume_button.setToolTip('Volumen')
        
        self.btn_config = QPushButton()
        self.btn_config.setIcon(QIcon.fromTheme('preferences-system'))
        self.btn_config.setToolTip('Configuración')

        # Configurar tamaño de todos los botones
        for button in [self.btn_load, self.btn_play, self.btn_pause, 
                      self.btn_stop, self.btn_playlist, 
                      self.volume_button, self.btn_config]:
            button.setFixedSize(button_size, button_size)
            button.setIconSize(QSize(icon_size, icon_size))

        # Conectar señales de los botones
        self.btn_load.clicked.connect(self.load_file)
        self.btn_play.clicked.connect(self.play_audio)
        self.btn_pause.clicked.connect(self.pause_audio)
        self.btn_stop.clicked.connect(self.stop_audio)
        self.btn_playlist.clicked.connect(self.show_playlist)
        self.btn_config.clicked.connect(self.show_config)
        
        # Ahora podemos cargar la geometría
        self.load_saved_geometry()

    def load_saved_geometry(self):
        """Carga la geometría guardada del archivo JSON"""
        try:
            state = load_window_state('main_player', (100, 100, 600, 200))
            self.setGeometry(state['x'], state['y'], state['width'], state['height'])
            if state['state']:
                self.setWindowState(Qt.WindowState(state['state']))
        except Exception as e:
            print(f"Error al cargar geometría: {e}")

        self.setMinimumSize(400, 150)  # Tamaño mínimo para que se vean todos los controles
        pygame.mixer.init()
        self.current_file = None
        self.is_paused = False
        self.audio_length = 0

        # Definir tamaños de botones e iconos al inicio
        button_size = 24
        icon_size = 16

        # Configurar botones sin estilos individuales
        for button in [self.btn_load, self.btn_play, self.btn_pause, 
                      self.btn_stop, self.btn_playlist, 
                      self.volume_button, self.btn_config]:
            button.setFixedSize(button_size, button_size)
            button.setIconSize(QSize(icon_size, icon_size))
            
        # Eliminar todos los setStyleSheet() individuales de los botones
        
        # Crear el menú desplegable para el volumen
        self.volume_menu = QMenu(self)
        
        # Configurar el slider vertical y su contenedor
        self.volume_widget = QWidget()
        self.volume_layout = QVBoxLayout(self.volume_widget)
        self.volume_layout.setContentsMargins(4, 4, 4, 4)
        self.volume_layout.setSpacing(0)
        
        self.volume_slider = QSlider(Qt.Vertical)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedSize(20, 100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.volume_slider.valueChanged.connect(self.update_volume_icon)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:vertical {
                width: 4px;
                background: #ccc;
                margin: 0px;
            }
            QSlider::handle:vertical {
                background: #2196F3;
                height: 10px;
                width: 10px;
                margin: 0 -3px;
                border-radius: 5px;
            }
        """)
        
        self.volume_layout.addWidget(self.volume_slider, alignment=Qt.AlignCenter)
        
        # Crear un QWidgetAction con el tamaño ajustado
        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(self.volume_widget)
        self.volume_menu.addAction(widget_action)
        self.volume_menu.setFixedWidth(28)

        # Conectar el botón con la función que muestra el menú
        self.volume_button.clicked.connect(self.show_volume_menu)

        # Agregar botón de configuración
        self.btn_config = QPushButton()
        self.btn_config.setIcon(QIcon.fromTheme('preferences-system'))
        self.btn_config.setToolTip('Configuración')
        self.btn_config.clicked.connect(self.show_config)
        self.btn_config.setFixedSize(button_size, button_size)
        self.btn_config.setIconSize(QSize(icon_size, icon_size))

        # Crear ventana de configuración
        self.config_window = ConfigWindow(self)
        
        # Configurar tamaño de botones e iconos
        button_size = 24
        icon_size = 16
        for button in [self.btn_load, self.btn_play, self.btn_pause, self.btn_stop, self.btn_playlist]:
            button.setFixedSize(button_size, button_size)
            button.setIconSize(QSize(icon_size, icon_size))

        # Crear la barra de reproducción (seekbar)
        self.seekbar = QSlider(Qt.Horizontal)
        self.seekbar.setMinimum(0)
        self.seekbar.setMaximum(100)
        self.seekbar.setValue(0)
        self.seekbar.setEnabled(False)
        self.seekbar.sliderReleased.connect(self.seek_audio)
        self.seekbar.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #ccc;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)

        # Modificar el layout de botones
        buttons_layout = QHBoxLayout()
        # Layout izquierdo para el botón de cargar
        left_layout = QHBoxLayout()
        left_layout.addWidget(self.btn_load)
        left_layout.addStretch()
        
        # Layout central para los botones de control
        center_layout = QHBoxLayout()
        center_layout.addWidget(self.btn_play)
        center_layout.addWidget(self.btn_pause)
        center_layout.addWidget(self.btn_stop)
        center_layout.addWidget(self.btn_playlist)
        
        # Layout derecho para volumen y configuración
        right_layout = QHBoxLayout()
        right_layout.addStretch()
        right_layout.addWidget(self.volume_button)
        right_layout.addWidget(self.btn_config)
        
        # Agregar los tres layouts al layout principal de botones
        buttons_layout.addLayout(left_layout)
        buttons_layout.addLayout(center_layout)
        buttons_layout.addLayout(right_layout)
        
        # Layout principal
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.seekbar)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_seekbar)

        # Agregamos la lista de reproducción
        self.playlist_window = PlaylistWindow()
        self.playlist = []
        # Conectar señales
        self.playlist_window.play_signal.connect(self.play_from_playlist)
        self.playlist_window.add_file_signal.connect(self.add_file_to_playlist)

        self.setAcceptDrops(True)  # Habilitar drops en la ventana principal

    def show_playlist(self):
        """Muestra la ventana de la lista de reproducción"""
        self.playlist_window.show()

    def sync_playlist_with_widget(self):
        """Sincroniza la lista interna con el orden visual del QListWidget."""
        new_playlist = []
        for i in range(self.playlist_window.playlist.count()):
            item = self.playlist_window.playlist.item(i)
            new_playlist.append(item.toolTip())  # Obtiene la ruta completa del archivo
        self.playlist = new_playlist  # Actualiza la lista interna

    def play_from_playlist(self, index):
        """Reproduce el archivo desde la lista de reproducción."""
        try:
            index = int(index)
            # Obtener el archivo directamente del QListWidget
            if 0 <= index < self.playlist_window.playlist.count():
                filename = self.playlist_window.playlist.item(index).toolTip()
                if os.path.exists(filename):
                    self.current_file = filename
                    self.label.setText(os.path.basename(filename))
                    pygame.mixer.music.load(filename)
                    pygame.mixer.music.play()
                    self.is_paused = False
                    self.btn_play.setEnabled(False)
                    self.btn_pause.setEnabled(True)
                    self.btn_stop.setEnabled(True)
                    self.seekbar.setEnabled(True)
                    self.update_audio_length()
                    self.timer.start()  # Iniciamos el timer para actualizar la barra
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al reproducir el archivo: {str(e)}")

    def load_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Selecciona un archivo de audio", "", "Audio Files (*.mp3 *.wav)")
        if filename:
            # Agregar el archivo a la lista de reproducción primero
            self.add_file_to_playlist(filename)
            
            # Establecer como archivo actual
            self.current_file = filename
            display_name = os.path.basename(filename)
            if len(display_name) > 50:
                display_name = display_name[:47] + "..."
            self.label.setText(display_name)
            self.label.setToolTip(filename)
            
            self.btn_play.setEnabled(True)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.seekbar.setEnabled(True)
            self.seekbar.setValue(0)
            self.stop_audio()
            
            try:
                if filename.lower().endswith('.mp3'):
                    audio = MP3(filename)
                else:
                    audio = WAVE(filename)
                self.audio_length = int(audio.info.length)
                self.seekbar.setMaximum(self.audio_length)
            except Exception:
                self.audio_length = 0
                self.seekbar.setMaximum(100)

    def add_file_to_playlist(self, filename):
        """Agrega un archivo a la lista de reproducción"""
        # Verificar si el archivo existe en el sistema
        if not os.path.exists(filename):
            return
        
        # Verificar si el archivo ya está en la lista visual actual
        for i in range(self.playlist_window.playlist.count()):
            if self.playlist_window.playlist.item(i).toolTip() == filename:
                return  # Solo retorna si el archivo está actualmente en la lista
    
        # Agregar a la lista interna si no está
        if filename not in self.playlist:
            self.playlist.append(filename)
    
        # Agregar al widget visual
        item = QListWidgetItem(os.path.basename(filename))
        item.setToolTip(filename)
        self.playlist_window.playlist.addItem(item)
        
        # Si es el primer archivo o no hay archivo actual
        if len(self.playlist) == 1 or not self.current_file:
            self.current_file = filename
            display_name = os.path.basename(filename)
            if len(display_name) > 50:
                display_name = display_name[:47] + "..."
            self.label.setText(display_name)
            self.label.setToolTip(filename)
            self.btn_play.setEnabled(True)
            self.btn_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.seekbar.setEnabled(True)
            
            try:
                if filename.lower().endswith('.mp3'):
                    audio = MP3(filename)
                else:
                    audio = WAVE(filename)
                self.audio_length = int(audio.info.length)
                self.seekbar.setMaximum(self.audio_length)
            except Exception:
                self.audio_length = 0
                self.seekbar.setMaximum(100)

    def play_audio(self):
        """Reproduce el audio actual o el primero de la lista si no hay actual"""
        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
        else:
            try:
                # Si no hay archivo actual pero hay archivos en la lista, reproducir el primero
                if not self.current_file and self.playlist_window.playlist.count() > 0:
                    first_item = self.playlist_window.playlist.item(0)
                    self.current_file = first_item.toolTip()
                    self.label.setText(os.path.basename(self.current_file))
            
                if self.current_file:
                    pygame.mixer.music.load(self.current_file)
                    pygame.mixer.music.play()
                    self.update_audio_length()  # Actualizar la duración del audio
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error al reproducir: {str(e)}")
                return
    
        # Actualizar estado de los botones
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.seekbar.setEnabled(True)
        self.timer.start()

    def pause_audio(self):
        """Pausa el audio actual"""
        if self.current_file and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.is_paused = True
            self.timer.stop()
            
            # Actualizar estado de los botones
            self.btn_play.setEnabled(True)
            self.btn_pause.setEnabled(False)

    def stop_audio(self):
        """Detiene la reproducción y limpia el estado del reproductor"""
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        pygame.mixer.quit()
        pygame.mixer.init()
        
        # Limpiar la interfaz del reproductor pero mantener la lista
        self.label.setText("No hay archivo cargado")
        self.is_paused = False
        self.seekbar.setValue(0)
        self.timer.stop()
        
        # Mantener los botones habilitados si hay archivos en la lista
        if self.playlist_window.playlist.count() > 0:
            self.btn_play.setEnabled(True)
            self.current_file = None  # Limpiar archivo actual para que play_audio use el primero de la lista
        else:
            self.btn_play.setEnabled(False)
            self.current_file = None
    
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.seekbar.setEnabled(False)

    def seek_audio(self):
        if self.current_file and self.audio_length > 0:
            value = self.seekbar.value()
            pygame.mixer.music.play(start=int(value))
            self.is_paused = False
            self.timer.start()

    def update_seekbar(self):
        if pygame.mixer.music.get_busy() and not self.seekbar.isSliderDown():
            pos = pygame.mixer.music.get_pos() // 1000
            self.seekbar.setValue(pos)
        elif not pygame.mixer.music.get_busy() and not self.seekbar.isSliderDown():
            self.seekbar.setValue(0)
            self.timer.stop()

    def move_audio(self, old_index, new_index):
        """Mueve un archivo de audio en la lista de reproducción"""
        if 0 <= old_index < len(self.playlist) and 0 <= new_index < len(self.playlist):
            # Detener la reproducción si es necesario
            was_playing = pygame.mixer.music.get_busy()
            if was_playing:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        
            # Mover el archivo en la lista interna
            file_to_move = self.playlist.pop(old_index)
            self.playlist.insert(new_index, file_to_move)
            
            # Si el archivo movido es el que se está reproduciendo
            if self.current_file == file_to_move and was_playing:
                pygame.mixer.music.load(self.current_file)
                pygame.mixer.music.play()

    def remove_audio(self, index):
        """Elimina un archivo de la lista de reproducción"""
        if 0 <= index < len(self.playlist):
            # Detener reproducción actual si es necesario
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                pygame.mixer.unload()
                pygame.mixer.quit()
                pygame.mixer.init()
        
            # Eliminar el archivo de la lista
            file_to_remove = self.playlist.pop(index)
            
            # Si el archivo eliminado es el que se está reproduciendo
            if self.current_file == file_to_remove:
                self.current_file = None
                self.label.setText("No hay archivo cargado")
                self.btn_play.setEnabled(False)
                self.btn_pause.setEnabled(False)
                self.btn_stop.setEnabled(False)
                self.seekbar.setEnabled(False)
                self.seekbar.setValue(0)
                self.timer.stop()

    def change_volume(self):
        """Cambia el volumen de reproducción"""
        volume = self.volume_slider.value() / 100.0  # Convertir a rango 0-1
        pygame.mixer.music.set_volume(volume)

    def show_config(self):
        """Muestra la ventana de configuración"""
        self.config_window.exec_()

    def quit_application(self):
        """Cierra completamente la aplicación"""
        QApplication.quit()

    def changeEvent(self, event):
        """Maneja el evento de minimización de la ventana"""
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                if self.settings.value('minimize_to_tray', False, type=bool):
                    self.hide()
                    event.ignore()
                else:
                    event.accept()
            else:
                event.accept()

    def activateFromTray(self, reason):
        """Maneja los clicks en el icono de la bandeja"""
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            self.show()
            self.setWindowState(Qt.WindowActive)
            self.activateWindow()
            self.raise_()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Acepta el arrastre si son archivos de audio"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(('.mp3', '.wav')):
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """Procesa los archivos soltados"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        for file_path in files:
            if file_path.lower().endswith(('.mp3', '.wav')):
                # Si es el primer archivo, cargarlo en el reproductor
                if not self.current_file:
                    self.current_file = file_path
                    self.label.setText(os.path.basename(file_path))
                    self.btn_play.setEnabled(True)
                    self.btn_pause.setEnabled(True)
                    self.btn_stop.setEnabled(True)
                    self.seekbar.setEnabled(True)
                    try:
                        if file_path.lower().endswith('.mp3'):
                            audio = MP3(file_path)
                        else:
                            audio = WAVE(file_path)
                        self.audio_length = int(audio.info.length)
                        self.seekbar.setMaximum(self.audio_length)
                    except Exception:
                        self.audio_length = 0
                        self.seekbar.setMaximum(100)
                
                # Agregar el archivo a la lista de reproducción
                self.add_file_to_playlist(file_path)

    def show_volume_menu(self):
        """Muestra el menú de volumen debajo del botón"""
        pos = self.volume_button.mapToGlobal(self.volume_button.rect().bottomLeft())
        self.volume_menu.exec_(pos)

    def update_volume_icon(self):
        """Actualiza el icono del botón de volumen según el nivel"""
        volume = self.volume_slider.value()
        if volume == 0:
            self.volume_button.setIcon(QIcon.fromTheme('audio-volume-muted'))
        elif volume < 33:
            self.volume_button.setIcon(QIcon.fromTheme('audio-volume-low'))
        elif volume < 66:
            self.volume_button.setIcon(QIcon.fromTheme('audio-volume-medium'))
        else:
            self.volume_button.setIcon(QIcon.fromTheme('audio-volume-high'))

    def apply_equalization(self, eq_values):
        """Aplica una ecualización básica usando pygame.mixer"""
        if not self.current_file or not pygame.mixer.music.get_busy():
            return
            
        try:
            # Guardar posición actual
            current_pos = pygame.mixer.music.get_pos() / 1000.0
            
            # Aplicar cambios básicos de frecuencia
            # Bajo (hasta 250Hz)
            bass = sum(eq_values.get(f, 0) for f in ['60Hz', '170Hz']) / 2
            # Medio (250Hz - 4kHz)
            mid = sum(eq_values.get(f, 0) for f in ['310Hz', '600Hz', '1kHz', '3kHz']) / 4
            # Alto (4kHz y superior)
            treble = sum(eq_values.get(f, 0) for f in ['6kHz', '12kHz', '14kHz', '16kHz']) / 4
            
            # Configurar los canales de pygame
            pygame.mixer.set_num_channels(3)  # Un canal para cada rango
            
            # Ajustar volúmenes relativos
            bass_vol = max(0, min(1.0, (bass + 12) / 24))  # Convertir de -12/+12 a 0-1
            mid_vol = max(0, min(1.0, (mid + 12) / 24))
            treble_vol = max(0, min(1.0, (treble + 12) / 24))
            
            # Aplicar los volúmenes
            pygame.mixer.Channel(0).set_volume(bass_vol)    # Bajos
            pygame.mixer.Channel(1).set_volume(mid_vol)     # Medios
            pygame.mixer.Channel(2).set_volume(treble_vol)  # Altos
            
            # Recargar y reproducir
            pygame.mixer.music.load(self.current_file)
            pygame.mixer.music.play(start=current_pos)
            
        except Exception as e:
            print(f"Error al aplicar ecualización: {e}")

    def update_playlist_order(self, old_index, new_index):
        """Actualiza el orden de la lista interna cuando se mueven elementos"""
        if 0 <= old_index < len(self.playlist) and 0 <= new_index < len(self.playlist):
            # Mover el elemento en la lista interna
            item = self.playlist.pop(old_index)
            self.playlist.insert(new_index, item)
            
            # Si el archivo que se está reproduciendo es el que se movió
            if self.current_file == item:
                # Actualizar la interfaz si es necesario
                self.label.setText(os.path.basename(item))

    def update_audio_length(self):
        """Actualiza la duración del audio actual"""
        try:
            if self.current_file:
                if self.current_file.lower().endswith('.mp3'):
                    audio = MP3(self.current_file)
                else:
                    audio = WAVE(self.current_file)
                self.audio_length = int(audio.info.length)
                self.seekbar.setMaximum(self.audio_length)
        except Exception as e:
            print(f"Error al actualizar la duración del audio: {e}")
            self.audio_length = 0
            self.seekbar.setMaximum(100)

class ConfigWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        
        # Obtener la ruta del ícono
        icon_path = get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(QIcon.fromTheme('audio-x-generic'))

        self.eq_sliders = {}  # Agregar este atributo para acceder a los sliders
        self.settings = QSettings('Player', 'AudioPlayer')
        self.init_ui()
        self.load_saved_geometry()
        self.load_eq_settings()  # Cargar valores guardados de ecualización

    def save_settings(self):
        """Guarda las configuraciones cuando cambian"""
        self.settings.setValue('startup', self.startup_check.isChecked())
        self.settings.setValue('minimize_to_tray', self.minimize_check.isChecked())
        
        # Configurar inicio automático
        if sys.platform == 'linux':
            autostart_path = os.path.expanduser('~/.config/autostart/')
            desktop_file = os.path.join(autostart_path, 'audioplayer.desktop')
            
            if self.startup_check.isChecked():
                # Crear directorio si no existe
                os.makedirs(autostart_path, exist_ok=True)
                
                # Crear archivo .desktop
                with open(desktop_file, 'w') as f:
                    f.write(f"""[Desktop Entry]
Type=Application
Name=Audio Player
Exec={sys.argv[0]}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
""")
            else:
                # Eliminar archivo .desktop si existe
                if os.path.exists(desktop_file):
                    os.remove(desktop_file)

    def save_eq_settings(self):
        """Guarda los valores de ecualización"""
        eq_values = {}
        for freq, slider in self.eq_sliders.items():
            eq_values[freq] = slider.value()
        self.settings.setValue('equalizer', eq_values)
        # Emitir señal al reproductor para actualizar el audio
        if isinstance(self.parent(), AudioPlayer):
            self.parent().apply_equalization(eq_values)

    def load_eq_settings(self):
        """Carga los valores guardados de ecualización"""
        eq_values = self.settings.value('equalizer', {}, type=dict)
        if eq_values:
            for freq, value in eq_values.items():
                if freq in self.eq_sliders:
                    self.eq_sliders[freq].setValue(int(value))

    def apply_preset(self, preset_name):
        """Aplica un preset de ecualización predefinido"""
        presets = {
            "Plano": {freq: 0 for freq in self.eq_sliders.keys()},
            "Rock": {
                "60Hz": 4, "170Hz": 3, "310Hz": -2, "600Hz": -3,
                "1kHz": 2, "3kHz": 4, "6kHz": 3, "12kHz": 4,
                "14kHz": 4, "16kHz": 4
            },
            "Pop": {
                "60Hz": -1, "170Hz": -1, "310Hz": 0, "600Hz": 2,
                "1kHz": 3, "3kHz": 2, "6kHz": 1, "12kHz": 1,
                "14kHz": 2, "16kHz": 2
            },
            "Jazz": {
                "60Hz": 2, "170Hz": 1, "310Hz": 1, "600Hz": 2,
                "1kHz": -1, "3kHz": -1, "6kHz": 0, "12kHz": 1,
                "14kHz": 2, "16kHz": 3
            },
            "Clásica": {
                "60Hz": 3, "170Hz": 2, "310Hz": 1, "600Hz": 0,
                "1kHz": 0, "3kHz": 0, "6kHz": -1, "12kHz": -1,
                "14kHz": -2, "16kHz": -2
            }
        }
        
        if preset_name in presets:
            for freq, value in presets[preset_name].items():
                if freq in self.eq_sliders:
                    self.eq_sliders[freq].setValue(value)
            self.save_eq_settings()

    def init_ui(self):
        # Crear el widget de pestañas
        tab_widget = QTabWidget()

        # Crear la pestaña "General"
        general_tab = QWidget()
        general_layout = QVBoxLayout()

        # Contenido de la pestaña "General"
        self.startup_check = QCheckBox("Iniciar con el sistema")
        self.minimize_check = QCheckBox("Minimizar a la bandeja del sistema al minimizar")

        # Cargar estado guardado de los checkboxes
        self.startup_check.setChecked(self.settings.value('startup', False, type=bool))
        self.minimize_check.setChecked(self.settings.value('minimize_to_tray', False, type=bool))

        # Conectar señales de cambio
        self.startup_check.stateChanged.connect(self.save_settings)
        self.minimize_check.stateChanged.connect(self.save_settings)

        general_layout.addWidget(self.startup_check)
        general_layout.addWidget(self.minimize_check)
        general_layout.addStretch()

        general_tab.setLayout(general_layout)

        # Crear la pestaña "Equalización"
        eq_tab = QWidget()
        eq_layout = QVBoxLayout()
    
        # Crear sliders para la ecualización
        frequencies = ['60Hz', '170Hz', '310Hz', '600Hz', '1kHz', '3kHz', '6kHz', '12kHz', '14kHz', '16kHz']
        eq_sliders = {}
    
        slider_layout = QHBoxLayout()
        for freq in frequencies:
            slider_container = QVBoxLayout()
            
            slider = QSlider(Qt.Vertical)
            slider.setMinimum(-12)
            slider.setMaximum(12)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBothSides)
            slider.setTickInterval(3)

            freq_label = QLabel(freq)
            value_label = QLabel("0 dB")
            value_label.setAlignment(Qt.AlignCenter)
            
            # Conectar el cambio de valor
            slider.valueChanged.connect(lambda v, l=value_label: l.setText(f"{v} dB"))
            slider.valueChanged.connect(self.save_eq_settings)
            
            self.eq_sliders[freq] = slider
            
            slider_container.addWidget(value_label)
            slider_container.addWidget(slider)
            slider_container.addWidget(freq_label)
            
            slider_layout.addLayout(slider_container)

        # Modificar la parte de presets
        preset_layout = QHBoxLayout()
        presets = ["Plano", "Rock", "Pop", "Jazz", "Clásica"]
        
        for preset in presets:
            btn = QPushButton(preset)
            btn.clicked.connect(lambda checked, p=preset: self.apply_preset(p))
            preset_layout.addWidget(btn)
    
        eq_layout.addLayout(slider_layout)
        eq_layout.addLayout(preset_layout)
    
        eq_tab.setLayout(eq_layout)
    
        
        # Crear la pestaña "Acerca de" (código existente)
        about_tab = QWidget()
        about_layout = QVBoxLayout()
    
        # Agregar el icono
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icons', 'icon.png')
        icon_label = QLabel()
        icon_pixmap = QPixmap(icon_path)
        if not icon_pixmap.isNull():
            icon_pixmap = icon_pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(icon_pixmap)
            icon_label.setAlignment(Qt.AlignCenter)
            about_layout.addWidget(icon_label)
    
        app_name = QLabel("Hero Music")
        app_name.setStyleSheet("font-size: 16px; font-weight: bold;")
    
        version = QLabel("Versión 1.0")
        author = QLabel("Desarrollado por: B&R.Comp")
        description = QLabel("Un reproductor de audio simple y elegante\n"
                       "con soporte para archivos MP3 y WAV.")
    
        about_layout.addWidget(app_name, alignment=Qt.AlignCenter)
        about_layout.addWidget(version, alignment=Qt.AlignCenter)
        about_layout.addWidget(author, alignment=Qt.AlignCenter)
        about_layout.addWidget(description, alignment=Qt.AlignCenter)
        about_layout.addStretch()
    
        about_tab.setLayout(about_layout)
    
        # Agregar todas las pestañas al widget
        tab_widget.addTab(general_tab, "General")
        tab_widget.addTab(eq_tab, "Ecualización")
        tab_widget.addTab(about_tab, "Acerca de")
    
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.addWidget(tab_widget)
        self.setLayout(main_layout)

    def load_saved_geometry(self):
        """Carga la geometría guardada del archivo JSON"""
        try:
            state = load_window_state('config', (150, 150, 400, 300))
            self.setGeometry(state['x'], state['y'], state['width'], state['height'])
            if state['state']:
                self.setWindowState(Qt.WindowState(state['state']))
        except Exception as e:
            print(f"Error al cargar geometría: {e}")

    def closeEvent(self, event):
        """Guardar geometría al cerrar"""
        save_window_state('config', self.geometry(), self.windowState())
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Aplicar el estilo oscuro
    app.setStyleSheet(load_stylesheet())
    
    # Crear y mostrar el reproductor
    player = AudioPlayer()
    player.show()
    
    sys.exit(app.exec_())
