import { app, BrowserWindow, Tray, Menu, Notification, clipboard } from 'electron';
import path from 'path';
import Store from 'electron-store';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const store = new Store();
let mainWindow;
let tray;

function createWindow() {
  // Recuperar el tamaño y posición guardados
  const windowState = store.get('windowState', {
    width: 1000,
    height: 800,
    x: undefined,
    y: undefined
  });

  mainWindow = new BrowserWindow({
    width: windowState.width,
    height: windowState.height,
    x: windowState.x,
    y: windowState.y,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      partition: 'persist:whatsapp',
      // Añadir estas opciones
      enableWebSQL: true,
      webSecurity: true,
      webgl: true,
      images: true
    }
  });

  // Agregar CSS personalizado para mejorar la selección de texto
  mainWindow.webContents.on('dom-ready', () => {
    mainWindow.webContents.insertCSS(`
      * {
        user-select: text !important;
        -webkit-user-select: text !important;
      }
      ::selection {
        background: #2196F3 !important;
        color: white !important;
      }
    `);
  });

  // Guardar el tamaño y posición cuando la ventana se mueva o redimensione
  ['resize', 'move'].forEach(event => {
    mainWindow.on(event, () => {
      const bounds = mainWindow.getBounds();
      store.set('windowState', bounds);
    });
  });

  mainWindow.webContents.setUserAgent(
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
);
  mainWindow.loadURL('https://web.whatsapp.com');

  mainWindow.on('minimize', (event) => {
    event.preventDefault();
    mainWindow.hide();
  });

  mainWindow.on('close', () => {
  app.quit(); // Cierra toda la aplicación
});

  mainWindow.webContents.on('did-finish-load', () => {
    monitorMessages();
  });

  // Actualizar el menú contextual para que sea dinámico
  mainWindow.webContents.on('context-menu', async (e, params) => {
    const menuItems = [];

    // Opciones básicas de edición
    menuItems.push(
      { role: 'selectAll', label: 'Seleccionar todo' },
      { type: 'separator' },
      { role: 'copy', label: 'Copiar' },
      { role: 'cut', label: 'Cortar' },
      { role: 'paste', label: 'Pegar' }
    );

    // Mejorar la detección de imágenes
    if (params.mediaType === 'image' || params.srcURL?.match(/\.(jpg|jpeg|png|gif|webp)$/i)) {
      menuItems.push(
        { type: 'separator' },
        {
          label: 'Guardar imagen como...',
          click: async () => {
            const { dialog } = require('electron');
            const url = params.srcURL;
            
            try {
              const result = await dialog.showSaveDialog({
                defaultPath: `imagen_${Date.now()}.png`,
                filters: [
                  { name: 'Imágenes', extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp'] }
                ]
              });

              if (!result.canceled && url) {
                // Descargar la imagen
                mainWindow.webContents.downloadURL(url);
                mainWindow.webContents.session.once('will-download', (event, item) => {
                  item.setSavePath(result.filePath);
                  
                  item.on('done', (event, state) => {
                    if (state === 'completed') {
                      new Notification({
                        title: 'Descarga completada',
                        body: 'La imagen se ha guardado correctamente'
                      }).show();
                    }
                  });
                });
              }
            } catch (error) {
              console.error('Error al guardar la imagen:', error);
            }
          }
        }
      );
    }

    // Si hay una URL de imagen directa
    if (params.srcURL) {
      menuItems.push({
        label: 'Copiar URL de la imagen',
        click: () => clipboard.writeText(params.srcURL)
      });
    }

    // Si hay texto seleccionado
    if (params.selectionText) {
      menuItems.push(
        { type: 'separator' },
        {
          label: 'Guardar texto seleccionado',
          click: () => {
            const { dialog } = require('electron');
            dialog.showSaveDialog({
              defaultPath: 'texto_seleccionado.txt',
              filters: [{ name: 'Archivos de texto', extensions: ['txt'] }]
            }).then(result => {
              if (!result.canceled) {
                const fs = require('fs');
                fs.writeFileSync(result.filePath, params.selectionText);
              }
            });
          }
        }
      );
    }

    // Crear y mostrar el menú contextual
    const contextMenu = Menu.buildFromTemplate(menuItems);
    contextMenu.popup();
  });
}

function monitorMessages() {
  mainWindow.webContents.executeJavaScript(`
    setInterval(() => {
      const unread = document.querySelectorAll('[aria-label="Unread messages"]');
      if (unread.length > 0) {
        new Notification('WhatsApp', {
          body: 'Tienes nuevos mensajes',
          icon: '${path.join(__dirname, 'icon.png')}'
        }).show();
      }
    }, 10000);
  `);
}

app.whenReady().then(() => {
  createWindow();

  tray = new Tray(path.join(__dirname, 'icon.png'));
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Mostrar WhatsApp', click: () => mainWindow.show() },
    { label: 'Salir', click: () => app.quit() }
  ]);
  tray.setToolTip('WhatsApp Web');
  tray.setContextMenu(contextMenu);

  app.setLoginItemSettings({
    openAtLogin: true,
    path: app.getPath('exe')
  });

  new Notification({
    title: 'WhatsApp',
    body: '¡Tu aplicación está lista!',
    icon: path.join(__dirname, 'icon.png')
  }).show();
});

app.on('window-all-closed', () => {});
