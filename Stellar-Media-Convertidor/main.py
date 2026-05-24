import gi
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk
import subprocess
import os
import sys
import threading
import re
import time
from gi.repository import GLib
from gi.repository import GdkPixbuf

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class Converter(Gtk.Window):
    def __init__(self):
        super().__init__(title="Stellar Media Converter")
        self.set_border_width(0)

        # --- Cargar tamaño de ventana ---
        width, height = self.load_window_size()
        self.set_default_size(width, height)

        # --- Leer tema desde settings.conf ---
        conf_path = os.path.join(os.path.dirname(__file__), "settings.conf")
        tema = "Claro"
        if os.path.exists(conf_path):
            with open(conf_path, "r") as f:
                for line in f:
                    if line.startswith("tema="):
                        tema = line.strip().split("=")[1]

        # --- Cargar CSS según tema ---
        css_provider = Gtk.CssProvider()
        if tema == "Oscuro":
            css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style-dark.css")
        else:
            css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
        if os.path.exists(css_path):
            css_provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        # HeaderBar moderno
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)

        # Box vertical para título y subtítulo
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_label = Gtk.Label(label="Stellar Media Converter")
        title_label.get_style_context().add_class("header-title")
        subtitle_label = Gtk.Label(label="Convierte audio y video fácilmente")
        subtitle_label.get_style_context().add_class("header-subtitle")
        title_box.pack_start(title_label, False, False, 0)
        title_box.pack_start(subtitle_label, False, False, 0)

        header.set_custom_title(title_box)

        self.set_titlebar(header)

        # Icono (si existe)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "icon.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        # Layout principal: horizontal
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add(hbox)

        # Barra lateral izquierda para formatos con scroll
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_min_content_width(120)
        sidebar_scroll.set_max_content_width(120)
        sidebar_scroll.set_vexpand(True)
        hbox.pack_start(sidebar_scroll, False, False, 0)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar_scroll.add(sidebar)

        format_label = Gtk.Label(label="Formatos")
        format_label.set_margin_top(18)
        format_label.set_margin_bottom(8)
        format_label.set_halign(Gtk.Align.START)
        sidebar.pack_start(format_label, False, False, 0)

        self.formatos = [
            ("mp3", "audio-x-generic"),
            ("wav", "audio-x-generic"),
            ("ogg", "audio-x-generic"),
            ("flac", "audio-x-generic"),
            ("aac", "audio-x-generic"),
            ("wma", "audio-x-generic"),
            ("m4a", "audio-x-generic"),
            ("mp4", "video-x-generic"),
            ("avi", "video-x-generic"),
            ("mkv", "video-x-generic"),
            ("webm", "video-x-generic"),
            ("mov", "video-x-generic"),
            ("flv", "video-x-generic"),
            ("3gp", "video-x-generic"),
            ("mpg", "video-x-generic"),
            ("m4v", "video-x-generic"),
        ]
        self.selected_format = self.formatos[0][0]
        self.format_buttons = []

        icons_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

        for i, (fmt, icon_name) in enumerate(self.formatos):
            btn = Gtk.Button()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            custom_icon_file = os.path.join(icons_path, f"{fmt}.png")
            if os.path.exists(custom_icon_file):
                icon = Gtk.Image.new_from_file(custom_icon_file)
            else:
                icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
            label = Gtk.Label(label=fmt)
            box.pack_start(icon, False, False, 0)
            box.pack_start(label, False, False, 0)
            btn.add(box)
            btn.set_halign(Gtk.Align.FILL)
            btn.set_valign(Gtk.Align.FILL)
            btn.connect("clicked", self.on_format_selected, fmt)
            sidebar.pack_start(btn, False, False, 2)
            self.format_buttons.append(btn)
            btn.show_all()

        # Selección visual inicial
        self.format_buttons[0].set_name("selected_format")

        # Caja vertical principal para el resto de controles
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        vbox.set_margin_top(18)
        vbox.set_margin_bottom(18)
        vbox.set_margin_start(12)
        vbox.set_margin_end(28)
        hbox.pack_start(vbox, True, True, 0)

        # Entrada
        file_box = Gtk.Box(spacing=10)
        file_label = Gtk.Label(label="Archivo:")
        self.file_chooser = Gtk.FileChooserButton(title="Selecciona un archivo")
        file_box.pack_start(file_label, False, False, 0)
        file_box.pack_start(self.file_chooser, True, True, 0)
        vbox.pack_start(file_box, False, False, 0)

        # Carpeta de salida
        out_box = Gtk.Box(spacing=10)
        out_label = Gtk.Label(label="Carpeta salida:")
        self.output_chooser = Gtk.FileChooserButton(title="Selecciona carpeta de salida", action=Gtk.FileChooserAction.SELECT_FOLDER)
        out_box.pack_start(out_label, False, False, 0)
        out_box.pack_start(self.output_chooser, True, True, 0)
        vbox.pack_start(out_box, False, False, 0)

        # --- Cargar carpeta de salida predeterminada ---
        carpeta_pred = ""
        if os.path.exists(conf_path):
            with open(conf_path, "r") as f:
                for line in f:
                    if line.startswith("carpeta="):
                        carpeta_pred = line.strip().split("=", 1)[1]
        # Botón convertir
        self.convert_button = Gtk.Button(label="Convertir")
        self.convert_button.connect("clicked", self.convert_file)
        vbox.pack_start(self.convert_button, False, False, 0)

        # Mensaje
        self.status_label = Gtk.Label(label="")
        self.status_label.set_name("status")
        vbox.pack_start(self.status_label, False, False, 0)

        # Barra de progreso
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_size_request(-1, 28)  # Hace la barra más gruesa
        self.progress_bar.set_visible(False)
        vbox.pack_start(self.progress_bar, False, False, 0)

        # --- Botón de configuración pequeño en la parte inferior derecha ---
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_end(bottom_box, False, False, 0)

        config_button = Gtk.Button()
        icon = Gtk.Image.new_from_icon_name("emblem-system", Gtk.IconSize.SMALL_TOOLBAR)
        config_button.add(icon)  # <-- corregido para GTK3
        config_button.set_relief(Gtk.ReliefStyle.NONE)
        config_button.set_tooltip_text("Configuración")
        config_button.set_size_request(24, 24)
        config_button.connect("clicked", self.on_config_clicked)
        bottom_box.pack_end(config_button, False, False, 0)
        # ---------------------------------------------------------------

        self.connect("configure-event", self.on_configure_event)

        if carpeta_pred:
            self.output_chooser.set_filename(carpeta_pred)

    def load_window_size(self):
        conf_path = os.path.join(os.path.dirname(__file__), "window.conf")
        try:
            with open(conf_path, "r") as f:
                line = f.readline()
                width, height = map(int, line.strip().split(","))
                return width, height
        except Exception:
            return 480, 260  # Tamaño por defecto

    def on_configure_event(self, widget, event):
        # Guardar tamaño al cambiar
        width = self.get_size()[0]
        height = self.get_size()[1]
        conf_path = os.path.join(os.path.dirname(__file__), "window.conf")
        try:
            with open(conf_path, "w") as f:
                f.write(f"{width},{height}")
        except Exception:
            pass
        return False

    def on_format_selected(self, button, fmt):
        self.selected_format = fmt
        # Actualiza el estilo visual del botón seleccionado
        for btn in self.format_buttons:
            btn.set_name("")
        button.set_name("selected_format")

    def convert_file(self, widget):
        input_file = self.file_chooser.get_filename()
        output_folder = self.output_chooser.get_filename()
        output_format = self.selected_format

        if not input_file or not output_folder:
            self.status_label.set_text("⚠️ Selecciona archivo y carpeta de salida")
            return

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_folder, f"{base_name}.{output_format}")

        # Obtener duración del archivo
        duration = self.get_duration(input_file)
        if duration == 0:
            self.status_label.set_text("❌ No se pudo obtener la duración del archivo")
            return

        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Convirtiendo...")

        # Ejecutar FFmpeg en un hilo para no bloquear la interfaz
        thread = threading.Thread(target=self.run_ffmpeg, args=(input_file, output_file, duration))
        thread.start()

    def get_duration(self, input_file):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return float(result.stdout.strip())
        except Exception:
            return 0

    def run_ffmpeg(self, input_file, output_file, duration):
        cmd = ["ffmpeg", "-i", input_file, output_file]
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

        time_regex = re.compile(r"time=(\d+):(\d+):(\d+).(\d+)")

        for line in proc.stderr:
            match = time_regex.search(line)
            if match:
                h, m, s, ms = map(int, match.groups())
                current = h * 3600 + m * 60 + s + ms / 100
                fraction = min(current / duration, 1.0)
                # Actualizar barra de progreso en el hilo principal
                GLib.idle_add(self.progress_bar.set_fraction, fraction)
                GLib.idle_add(self.progress_bar.set_text, f"{int(fraction*100)}%")

        proc.wait()
        GLib.idle_add(self.progress_bar.set_visible, False)
        if proc.returncode == 0:
            GLib.idle_add(self.status_label.set_text, f"✅ Conversión completada: {output_file}")
        else:
            GLib.idle_add(self.status_label.set_text, "❌ Error en la conversión")

    def on_config_clicked(self, widget):
        dialog = Gtk.Dialog(title="Configuración", parent=self, flags=0)
        dialog.set_default_size(400, 260)

        # Aplica el mismo estilo visual
        content_area = dialog.get_content_area()
        content_area.get_style_context().add_class("main-bg")

        notebook = Gtk.Notebook()
        content_area.add(notebook)

        # --- Pestaña Temas ---
        theme_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        theme_label = Gtk.Label(label="Selecciona el tema de la aplicación:")
        theme_box.pack_start(theme_label, False, False, 8)
        # Leer tema actual
        conf_path = os.path.join(os.path.dirname(__file__), "settings.conf")
        tema_actual = "Claro"
        if os.path.exists(conf_path):
            with open(conf_path, "r") as f:
                for line in f:
                    if line.startswith("tema="):
                        tema_actual = line.strip().split("=")[1]

        theme_combo = Gtk.ComboBoxText()
        theme_combo.append_text("Claro")
        theme_combo.append_text("Oscuro")
        theme_combo.set_active(0 if tema_actual == "Claro" else 1)
        theme_box.pack_start(theme_combo, False, False, 8)
        notebook.append_page(theme_box, Gtk.Label(label="Temas"))

        # --- Pestaña Carpeta de Salida Predeterminada ---
        folder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        folder_label = Gtk.Label(label="Carpeta de salida predeterminada:")
        folder_box.pack_start(folder_label, False, False, 8)
        folder_chooser = Gtk.FileChooserButton(title="Selecciona carpeta", action=Gtk.FileChooserAction.SELECT_FOLDER)
        folder_box.pack_start(folder_chooser, False, False, 8)
        notebook.append_page(folder_box, Gtk.Label(label="Carpeta de Salida"))

        # --- Pestaña Acerca de ---
        about_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        # Agregar icono
        about_icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "about.png")
        if os.path.exists(about_icon_path):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(about_icon_path)
            pixbuf = pixbuf.scale_simple(90, 90, GdkPixbuf.InterpType.BILINEAR)
            about_icon = Gtk.Image.new_from_pixbuf(pixbuf)
            about_box.pack_start(about_icon, False, False, 12)
        about_label = Gtk.Label(label="Stellar Media Converter\n\nDesarrollado por hero\nVersión 1.0\n2025")
        about_label.set_justify(Gtk.Justification.CENTER)
        about_box.pack_start(about_label, True, True, 24)
        notebook.append_page(about_box, Gtk.Label(label="Acerca de"))

        notebook.show_all()

        # Botón Guardar
        save_button = Gtk.Button(label="Guardar")
        save_button.set_halign(Gtk.Align.END)
        save_button.set_valign(Gtk.Align.END)
        content_area.pack_end(save_button, False, False, 12)
        save_button.show()

        def guardar_config(_):
            conf_path = os.path.join(os.path.dirname(__file__), "settings.conf")
            tema = theme_combo.get_active_text()
            carpeta = folder_chooser.get_filename() or ""
            with open(conf_path, "w") as f:
                f.write(f"tema={tema}\n")
                f.write(f"carpeta={carpeta}\n")
            # Recargar CSS (solo agrega el nuevo proveedor)
            css_provider = Gtk.CssProvider()
            if tema == "Oscuro":
                css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style-dark.css")
            else:
                css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
            if os.path.exists(css_path):
                css_provider.load_from_path(css_path)
                Gtk.StyleContext.add_provider_for_screen(
                    Gdk.Screen.get_default(),
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            # Aplicar carpeta de salida predeterminada al instante
            if carpeta:
                self.output_chooser.set_filename(carpeta)
            dialog.response(Gtk.ResponseType.OK)

        save_button.connect("clicked", guardar_config)

        dialog.run()
        dialog.destroy()

def main():
    win = Converter()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
