// Electron main process. Owns the app's window lifecycle and delegates
// backend process management to pythonServer.js.

const { app, BrowserWindow, Menu, dialog } = require('electron');
const path = require('path');
const { PythonServer, SERVER_URL, SERVER_PORT } = require('./pythonServer');

let mainWindow;
const pythonServer = new PythonServer();

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#05070c', // avoids a white flash while the server boots
    title: 'Aircraft Tracker',
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
      // Electron throttles timers/rendering in unfocused windows by
      // default (true), which causes issues for live tracking.
      backgroundThrottling: false,
    },
  });

  Menu.setApplicationMenu(null); // App window

  try {
    await pythonServer.waitUntilReady();
  } catch (err) {
    dialog.showErrorBox(
      'Backend not responding',
      `${err.message}\n\nCheck the terminal/console output for errors from the server ` +
      `package (a common cause is port ${SERVER_PORT} already being in use).`
    );
    // Fall through and try to load anyway — harmless if it fails, and
    // covers the case where the server came up just after the timeout.
  }

  mainWindow.loadURL(SERVER_URL);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  pythonServer.start(__dirname); // the `server` package lives alongside main.js
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  pythonServer.stop();
});
