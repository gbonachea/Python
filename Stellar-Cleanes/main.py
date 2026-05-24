import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QMessageBox, QCheckBox, QTextEdit, QSizePolicy
from PyQt5.QtCore import Qt
import clean

class CleanerGUI(QWidget):
    def scan_targets(self):
        """Actualiza la lista de elementos a limpiar detectando dinámicamente los candidatos."""
        self.list.clear()
        try:
            self.targets = list(clean.get_candidates()[0].keys())
            for t in self.targets:
                self.list.addItem(t)
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'No se pudieron detectar los elementos: {e}')

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Stellar Cleanes')
        from PyQt5.QtGui import QIcon, QPixmap
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.current_theme = 'Claro'
        # Cargar configuración (tema y tamaño)
        self.load_config()
        # Restaurar tamaño guardado o usar por defecto
        if hasattr(self, 'last_size'):
            self.resize(*self.last_size)
        else:
            self.setGeometry(100, 100, 700, 400)

        # Layouts principales
        main_layout = QVBoxLayout()
        content_layout = QHBoxLayout()

        # Lado izquierdo: opciones
        left_layout = QVBoxLayout()
        self.label = QLabel('Selecciona los elementos a limpiar:')
        left_layout.addWidget(self.label)
        self.list = QListWidget()
        self.list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.targets = list(clean.get_candidates()[0].keys())
        for t in self.targets:
            self.list.addItem(t)
        self.list.setSelectionMode(QListWidget.MultiSelection)
        left_layout.addWidget(self.list)
        self.include_system = QCheckBox('Incluir archivos de sistema')
        left_layout.addWidget(self.include_system)

        # Botón Escanear
        self.scan_btn = QPushButton('Escanear')
        self.scan_btn.setStyleSheet('''
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffb300, stop:1 #f57c00);
                color: white;
                font-weight: bold;
                font-size: 15px;
                border-radius: 8px;
                padding: 10px 24px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffd54f, stop:1 #ef6c00);
            }
        ''')
        self.scan_btn.clicked.connect(self.scan_targets)
        left_layout.addWidget(self.scan_btn)
        left_layout.addStretch()

        # Lado derecho: proceso/resultados
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel('Proceso de limpieza:'))
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.result_text)

        # Indicadores de totales debajo del cuadro de proceso
        totals_layout = QHBoxLayout()
        self.label_total_a_limpiar = QPushButton('Total a limpiar: 0 B')
        self.label_total_a_limpiar.setEnabled(False)
        self.label_total_a_limpiar.setStyleSheet('font-weight: bold; font-size: 15px; color: #1565c0; background: #e3f2fd; border: 2px solid #90caf9; border-radius: 8px; padding: 10px 18px;')
        self.label_total_limpiado = QPushButton('Total limpiado: 0 B')
        self.label_total_limpiado.setEnabled(False)
        self.label_total_limpiado.setStyleSheet('font-weight: bold; font-size: 15px; color: #388e3c; background: #e8f5e9; border: 2px solid #a5d6a7; border-radius: 8px; padding: 10px 18px;')
        totals_layout.addWidget(self.label_total_a_limpiar)
        totals_layout.addWidget(self.label_total_limpiado)
        right_layout.addLayout(totals_layout)

        # Botón de configuración en la parte inferior derecha
        right_layout.addStretch()  # Empuja el botón hacia abajo
        from PyQt5.QtGui import QIcon
        config_btn_layout = QHBoxLayout()
        config_btn_layout.addStretch()
        self.config_btn = QPushButton()
        self.config_btn.setIcon(QIcon('icons/configuracion.png'))
        self.config_btn.setIconSize(self.config_btn.sizeHint())
        self.config_btn.setToolTip('Configuración')
        self.config_btn.clicked.connect(self.open_config)
        config_btn_layout.addWidget(self.config_btn)
        right_layout.addLayout(config_btn_layout)

        # Añadir ambos lados al layout horizontal
        content_layout.addLayout(left_layout)
        content_layout.addLayout(right_layout)

        # Botones abajo
        buttons_layout = QHBoxLayout()
        self.simulate_btn = QPushButton('Simular limpieza')
        self.simulate_btn.setStyleSheet('''
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #42a5f5, stop:1 #1976d2);
                color: white;
                font-weight: bold;
                font-size: 15px;
                border-radius: 8px;
                padding: 10px 24px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #64b5f6, stop:1 #1565c0);
            }
        ''')
        self.simulate_btn.clicked.connect(self.simulate)
        buttons_layout.addWidget(self.simulate_btn)
        self.clean_btn = QPushButton('Limpiar')
        self.clean_btn.setStyleSheet('''
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #43a047, stop:1 #1b5e20);
                color: white;
                font-weight: bold;
                font-size: 15px;
                border-radius: 8px;
                padding: 10px 24px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #66bb6a, stop:1 #388e3c);
            }
        ''')
        self.clean_btn.clicked.connect(self.clean)
        buttons_layout.addWidget(self.clean_btn)
        buttons_layout.addStretch()

        # Ensamblar todo
        main_layout.addLayout(content_layout)
        main_layout.addLayout(buttons_layout)
        self.setLayout(main_layout)

    def open_config(self):
        from PyQt5.QtWidgets import QDialog, QTabWidget, QVBoxLayout, QLabel, QWidget, QComboBox, QTextEdit, QPushButton, QHBoxLayout
        from PyQt5.QtGui import QPixmap
        import os
        config_dialog = QDialog(self)
        config_dialog.setWindowTitle('Configuración')
        config_dialog.setMinimumWidth(400)
        config_dialog.setMinimumHeight(300)

        tabs = QTabWidget()

        # Pestaña Temas
        temas_tab = QWidget()
        temas_layout = QVBoxLayout()
        temas_layout.addWidget(QLabel('Selecciona un tema:'))
        theme_combo = QComboBox()
        theme_combo.addItems(['Claro', 'Oscuro', 'Sistema'])
        # Seleccionar el tema actual
        idx = theme_combo.findText(self.current_theme)
        if idx >= 0:
            theme_combo.setCurrentIndex(idx)
        temas_layout.addWidget(theme_combo)
        temas_tab.setLayout(temas_layout)
        tabs.addTab(temas_tab, 'Temas')

        # Función para aplicar el tema y guardar preferencia
        def apply_theme(theme):
            if theme == 'Claro':
                css_path = os.path.join('themes', 'light.css')
            elif theme == 'Oscuro':
                css_path = os.path.join('themes', 'dark.css')
            else:
                self.setStyleSheet("")
                self.current_theme = 'Sistema'
                self.save_theme()
                return
            try:
                with open(css_path, 'r') as f:
                    self.setStyleSheet(f.read())
                self.current_theme = theme
                self.save_theme()
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'No se pudo cargar el tema: {e}')

        # Cambiar tema al seleccionar
        theme_combo.currentTextChanged.connect(apply_theme)

        # Pestaña Acerca de
        about_tab = QWidget()
        about_layout = QVBoxLayout()
        # Mostrar el icono si existe
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')
        from PyQt5.QtGui import QPixmap
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            icon_label = QLabel()
            icon_label.setPixmap(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            icon_label.setAlignment(Qt.AlignCenter)
            about_layout.addWidget(icon_label)
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setPlainText('Stellar Cleanes\n\nVersión 1.0\nDesarrollado por tu equipo\n\nAplicación de limpieza para Linux Mint y otras distros.')
        about_layout.addWidget(about_text)
        about_tab.setLayout(about_layout)
        tabs.addTab(about_tab, 'Acerca de')



        # Layout principal del diálogo
        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(tabs)
        # Botón cerrar
        btn_close = QPushButton('Cerrar')
        btn_close.clicked.connect(config_dialog.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        dialog_layout.addLayout(btn_layout)
        config_dialog.setLayout(dialog_layout)
        config_dialog.exec_()

    def save_config(self):
        try:
            data = {'theme': self.current_theme, 'size': [self.width(), self.height()]}
            with open(self.config_path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    theme = data.get('theme', 'Claro')
                    self.current_theme = theme
                    size = data.get('size')
                    if size and isinstance(size, list) and len(size) == 2:
                        self.last_size = size
                    # Aplicar el tema al iniciar
                    if theme == 'Claro':
                        css_path = os.path.join('themes', 'light.css')
                    elif theme == 'Oscuro':
                        css_path = os.path.join('themes', 'dark.css')
                    else:
                        self.setStyleSheet("")
                        return
                    with open(css_path, 'r') as fcss:
                        self.setStyleSheet(fcss.read())
        except Exception:
            pass

    def save_theme(self):
        self.save_config()
    def closeEvent(self, event):
        self.save_config()
        super().closeEvent(event)

    def get_selected_targets(self):
        return [item.text() for item in self.list.selectedItems()]

    def simulate(self):
        targets = self.get_selected_targets()
        if not targets:
            QMessageBox.warning(self, 'Advertencia', 'Selecciona al menos un elemento.')
            self.label_total_a_limpiar.setText('Total a limpiar: 0 B')
            return
        to_show, total = clean.simulate_clean(targets, self.include_system.isChecked())
        msg = '\n'.join([f"{t}: {p} ({clean.human_size(size)})" for t, p, size in to_show])
        msg += f"\n\nTotal: {clean.human_size(total)}"
        self.result_text.setPlainText(msg)
        # Actualizar el texto del botón con formato llamativo
        self.label_total_a_limpiar.setText(f'💡 Total a limpiar: {clean.human_size(total)}')

    def clean(self):
        targets = self.get_selected_targets()
        if not targets:
            QMessageBox.warning(self, 'Advertencia', 'Selecciona al menos un elemento.')
            self.label_total_limpiado.setText('Total limpiado: 0 B')
            return
        reply = QMessageBox.question(self, 'Confirmar', '¿Estás seguro de limpiar los elementos seleccionados?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Antes de limpiar, obtener el total a limpiar
            to_show, total = clean.simulate_clean(targets, self.include_system.isChecked())
            clean.perform_clean(targets, self.include_system.isChecked(), force=True)
            QMessageBox.information(self, 'Limpieza', 'Limpieza completada.')
            self.result_text.setPlainText('')
            # Actualizar el texto del botón con formato llamativo
            self.label_total_limpiado.setText(f'✅ Total limpiado: {clean.human_size(total)}')

def main_gui():
    app = QApplication(sys.argv)
    gui = CleanerGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main_gui()
