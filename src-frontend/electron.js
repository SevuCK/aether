import { app, BrowserWindow } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';

// Fix for ES Modules (since we're using "type": "module")
const __dirname = path.dirname(fileURLToPath(import.meta.url));

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true, // Be careful with security here later!
      contextIsolation: false,
    },
  });

  // DEV MODE: Load the URL where Vite is serving Svelte
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173'); 
    mainWindow.webContents.openDevTools(); // Open Console automatically
  } 
  // PROD MODE: Load the static HTML file built by Svelte
  else {
    mainWindow.loadFile(path.join(__dirname, 'build', 'index.html'));
  }
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});