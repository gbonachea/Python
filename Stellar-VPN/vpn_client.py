import sys
import os
import subprocess
import signal
import json
import shutil
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QVBoxLayout, QHBoxLayout,
    QMessageBox, QDialog, QLineEdit, QCheckBox, QTabWidget, QListWidget, QFileDialog, QSystemTrayIcon,
    QMenu
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer

class VPNClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cliente VPN - StellarVPN")
        self.setGeometry(100, 100, 420, 480)
        self.setStyleSheet("background-color: #23272f;")
        
        # Configurar la ventana para mostrar los botones de la barra de título
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)
        
        # Crear el icono de la bandeja del sistema
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "icons.png")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            self.tray_icon.setIcon(icon)
        
        # Crear el menú contextual para el icono de la bandeja
        self.tray_menu = QMenu()
        self.restore_action = self.tray_menu.addAction("Restaurar")
        self.restore_action.triggered.connect(self.showNormal)
        self.tray_menu.addSeparator()
        self.quit_action = self.tray_menu.addAction("Salir")
        self.quit_action.triggered.connect(self.close_application)
        
        # Asignar el menú al icono de la bandeja
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        self.vpn_process = None
        self.ovpn_file = None
        self.init_ui()
        self.update_info()
        
        # Mostrar el icono en la bandeja
        self.tray_icon.show()

    def closeEvent(self, event):
        """Muestra un diálogo cuando se intenta cerrar la aplicación"""
        dialog = QMessageBox()
        dialog.setWindowTitle("Cerrar StellarVPN")
        dialog.setText("¿Qué desea hacer?")
        dialog.setIcon(QMessageBox.Question)
        
        # Personalizar los botones
        minimize_button = dialog.addButton("Minimizar a la bandeja", QMessageBox.ActionRole)
        close_button = dialog.addButton("Cerrar aplicación", QMessageBox.ActionRole)
        cancel_button = dialog.addButton("Cancelar", QMessageBox.RejectRole)
        
        # Establecer estilos para el diálogo y los botones
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: #23272f;
                color: #e0e0e0;
                min-width: 400px;
            }
            QMessageBox QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2c313c;
                color: #e0e0e0;
                border: none;
                padding: 5px 15px;
                min-width: 150px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #3c424f;
            }
            QPushButton:pressed {
                background-color: #4c525f;
            }
        """)
        
        dialog.exec_()
        
        if dialog.clickedButton() == minimize_button:
            # Minimizar a la bandeja sin notificación
            event.ignore()
            self.hide()
        elif dialog.clickedButton() == close_button:
            # Cerrar la aplicación
            if self.vpn_process:
                self.disconnect_vpn()
            self.tray_icon.hide()
            event.accept()
            QApplication.quit()
        else:
            # Cancelar la operación
            event.ignore()

    def tray_icon_activated(self, reason):
        """Maneja los clics en el icono de la bandeja"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()

    def close_application(self):
        """Cierra completamente la aplicación"""
        if self.vpn_process:
            self.disconnect_vpn()
        self.tray_icon.hide()
        QApplication.quit()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        vbox = QVBoxLayout()
        central_widget.setLayout(vbox)

        # Icono superior
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "icon.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
            icon_label = QLabel()
            icon_label.setPixmap(pixmap)
            icon_label.setAlignment(Qt.AlignCenter)
            vbox.addWidget(icon_label)

        label = QLabel("Selecciona el servidor para la conexion:")
        label.setStyleSheet("color: #e0e0e0; font-size: 14px;")
        vbox.addWidget(label)

        self.ovpn_files = self.get_ovpn_files()
        self.combobox = QComboBox()
        self.combobox.addItems(self.ovpn_files)
        self.combobox.currentIndexChanged.connect(self.on_select)
        vbox.addWidget(self.combobox)

        btn_hbox = QHBoxLayout()
        self.connect_btn = QPushButton("Conectar VPN")
        self.connect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self.connect_vpn)
        btn_hbox.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Desconectar VPN")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.disconnect_vpn)
        btn_hbox.addWidget(self.disconnect_btn)
        vbox.addLayout(btn_hbox)

        self.speed_btn = QPushButton("Velocidad: -- Mbps")
        self.speed_btn.setEnabled(False)
        vbox.addWidget(self.speed_btn)

        self.ip_btn = QPushButton("IP: -- | Puerto: --")
        self.ip_btn.setEnabled(False)
        vbox.addWidget(self.ip_btn)

        # Botón de configuración
        config_icon_path = os.path.join(os.path.dirname(__file__), "icons", "menu.png")
        config_btn = QPushButton()
        if os.path.exists(config_icon_path):
            config_btn.setIcon(QIcon(config_icon_path))
        else:
            config_btn.setText("⚙")
        config_btn.setFixedSize(30, 30)
        config_btn.clicked.connect(self.open_settings_window)
        vbox.addWidget(config_btn, alignment=Qt.AlignRight)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)
        self.timer.start(1000)

    def load_settings(self):
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    data = json.load(f)
                self.auto_start_var.setChecked(data.get("auto_start", False))
                self.auto_connect_var.setChecked(data.get("auto_connect", False))
                self.kill_switch_var.setChecked(data.get("kill_switch", False))
            except Exception:
                pass

    def save_settings(self):
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        data = {
            "auto_start": self.auto_start_var.isChecked(),
            "auto_connect": self.auto_connect_var.isChecked(),
            "kill_switch": self.kill_switch_var.isChecked()
        }
        try:
            with open(settings_path, "w") as f:
                json.dump(data, f)
            QMessageBox.information(self, "Ajustes", "Cambios guardados correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    def open_settings_window(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ajustes del aplicativo")
        dialog.setStyleSheet("background-color: #2c313c;")
        dialog.resize(400, 420)
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')
        tabs = QTabWidget(dialog)
        tabs.setStyleSheet("color: #e0e0e0;")
        vbox = QVBoxLayout(dialog)
        vbox.addWidget(tabs)
        dialog.setLayout(vbox)

        # Generales
        generales = QWidget()
        gen_layout = QVBoxLayout(generales)
        gen_label = QLabel("Ajustes generales")
        gen_label.setStyleSheet("font-size: 14px;")
        gen_layout.addWidget(gen_label)
        self.auto_start_var = QCheckBox("Iniciar automáticamente con el sistema")
        self.auto_connect_var = QCheckBox("Conectar automáticamente al iniciar")
        self.kill_switch_var = QCheckBox("Kill Switch (bloquear internet si la VPN se desconecta)")
        gen_layout.addWidget(self.auto_start_var)
        gen_layout.addWidget(self.auto_connect_var)
        gen_layout.addWidget(self.kill_switch_var)
        self.load_settings()
        guardar_btn = QPushButton("Guardar cambios")
        guardar_btn.clicked.connect(self.save_settings)
        gen_layout.addWidget(guardar_btn)
        tabs.addTab(generales, "Generales")

        # Servidores
        servidores = QWidget()
        serv_layout = QVBoxLayout(servidores)
        serv_label = QLabel("Lista de servidores disponibles")
        serv_label.setStyleSheet("font-size: 14px;")
        serv_layout.addWidget(serv_label)
        servers_list = QListWidget()
        ovpn_files = self.get_ovpn_files()
        servers_list.addItems(ovpn_files)
        serv_layout.addWidget(servers_list)
        eliminar_btn = QPushButton("Eliminar servidor")
        def eliminar_servidor():
            seleccion = servers_list.currentRow()
            if seleccion < 0:
                QMessageBox.warning(dialog, "Eliminar servidor", "Selecciona un servidor para eliminar.")
                return
            nombre = servers_list.item(seleccion).text()
            ruta = os.path.join(os.path.dirname(__file__), "ovpn", nombre)
            try:
                os.remove(ruta)
                servers_list.takeItem(seleccion)
                QMessageBox.information(dialog, "Eliminar servidor", f"Servidor '{nombre}' eliminado.")
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"No se pudo eliminar: {e}")
        eliminar_btn.clicked.connect(eliminar_servidor)
        serv_layout.addWidget(eliminar_btn)
        agregar_btn = QPushButton("Agregar servidor")
        def agregar_servidor():
            archivo, _ = QFileDialog.getOpenFileName(dialog, "Selecciona archivo .ovpn", "", "Archivos OVPN (*.ovpn)")
            if archivo:
                nombre = os.path.basename(archivo)
                destino = os.path.join(os.path.dirname(__file__), "ovpn", nombre)
                try:
                    shutil.copy2(archivo, destino)
                    servers_list.addItem(nombre)
                    QMessageBox.information(dialog, "Agregar servidor", f"Servidor '{nombre}' agregado.")
                except Exception as e:
                    QMessageBox.critical(dialog, "Error", f"No se pudo agregar: {e}")
        agregar_btn.clicked.connect(agregar_servidor)
        serv_layout.addWidget(agregar_btn)
        tabs.addTab(servidores, "Servidores")

        # Acerca de
        acerca = QWidget()
        acerca_layout = QVBoxLayout(acerca)
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio)
            icon_label = QLabel()
            icon_label.setPixmap(pixmap)
            acerca_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        acerca_label = QLabel("Cliente VPN StellarVPN\nVersión 1.0\nDesarrollado por B&R.Comp")
        acerca_label.setStyleSheet("font-size: 14px;")
        acerca_label.setAlignment(Qt.AlignCenter)
        acerca_layout.addWidget(acerca_label)
        tabs.addTab(acerca, "Acerca de")
        dialog.exec_()

    def get_ovpn_files(self):
        folder = os.path.join(os.path.dirname(__file__), "ovpn")
        if not os.path.exists(folder):
            return []
        return [f for f in os.listdir(folder) if f.endswith(".ovpn")]

    def on_select(self, index):
        if index >= 0:
            folder = os.path.join(os.path.dirname(__file__), "ovpn")
            self.ovpn_file = os.path.join(folder, self.combobox.currentText())
            self.connect_btn.setEnabled(True)
            QMessageBox.information(self, "Archivo seleccionado", f"Archivo: {self.ovpn_file}")

    def connect_vpn(self):
        if not self.ovpn_file:
            QMessageBox.critical(self, "Error", "Debes seleccionar un archivo .ovpn")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Autenticación requerida")
        dialog.resize(300, 120)
        vbox = QVBoxLayout(dialog)
        label = QLabel("Contraseña de sudo:")
        vbox.addWidget(label)
        password_entry = QLineEdit()
        password_entry.setEchoMode(QLineEdit.Password)
        vbox.addWidget(password_entry)
        def on_submit():
            password = password_entry.text()
            dialog.accept()
            try:
                self.vpn_process = subprocess.Popen(
                    ["sudo", "-S", "openvpn", "--config", self.ovpn_file],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.vpn_process.stdin.write((password + "\n").encode())
                self.vpn_process.stdin.flush()
                self.connect_btn.setEnabled(False)
                self.disconnect_btn.setEnabled(True)
                QMessageBox.information(self, "VPN", f"Conectando a la VPN con {self.ovpn_file} ...")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        submit_btn = QPushButton("Conectar")
        submit_btn.clicked.connect(on_submit)
        vbox.addWidget(submit_btn)
        dialog.exec_()

    def disconnect_vpn(self):
        if self.vpn_process:
            os.kill(self.vpn_process.pid, signal.SIGTERM)
            self.vpn_process = None
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            QMessageBox.information(self, "VPN", "VPN desconectada")

    def update_info(self):
        if self.vpn_process and self.vpn_process.poll() is None:
            velocidad = round(random.uniform(10, 100), 2)
            self.speed_btn.setText(f"Velocidad: {velocidad} Mbps")
            ip = "192.168.1.100"
            port = "1194"
            self.ip_btn.setText(f"IP: {ip} | Puerto: {port}")
        else:
            self.speed_btn.setText("Velocidad: -- Mbps")
            self.ip_btn.setText("IP: -- | Puerto: --")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Establecer el icono a nivel de aplicación
    icon_path = os.path.join(os.path.dirname(__file__), "icons", "icons.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = VPNClient()
    window.show()
    sys.exit(app.exec_())
