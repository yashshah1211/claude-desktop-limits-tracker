const { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow = null;
let pyServer = null;
let tray = null;
const PORT = 5173;

function startPythonBackend() {
  const scriptPath = path.join(__dirname, '..', 'web_server.py');
  pyServer = spawn('python', [scriptPath, '--no-browser'], {
    cwd: path.join(__dirname, '..')
  });

  pyServer.stdout.on('data', (data) => {
    console.log(`[Python] ${data}`);
  });

  pyServer.stderr.on('data', (data) => {
    console.error(`[Python Err] ${data}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 880,
    height: 720,
    minWidth: 580,
    minHeight: 600,
    backgroundColor: '#0e0e12',
    title: 'Claude.ai Limits Tracker - Windows',
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Give python server 500ms to bind port, then load
  setTimeout(() => {
    mainWindow.loadURL(`http://127.0.0.1:${PORT}`);
  }, 600);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (pyServer) {
    pyServer.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
