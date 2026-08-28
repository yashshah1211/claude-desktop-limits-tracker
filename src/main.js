const { app, BrowserWindow, dialog } = require('electron');
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

  pyServer.on('exit', (code) => {
    if (code && code !== 0 && mainWindow) {
      dialog.showErrorBox(
        'Claude.ai Limits Tracker',
        `Python backend exited unexpectedly (code ${code}).\nMake sure Python is installed and on your PATH.`
      );
    }
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

  let loadAttempts = 0;
  const MAX_LOAD_ATTEMPTS = 30;
  mainWindow.webContents.on('did-fail-load', (_event, _code, _desc, _url, isMainFrame) => {
    if (!isMainFrame) return;
    if (loadAttempts < MAX_LOAD_ATTEMPTS) {
      loadAttempts += 1;
      setTimeout(() => {
        if (mainWindow) mainWindow.loadURL(`http://127.0.0.1:${PORT}`);
      }, 1000);
    } else {
      mainWindow.loadFile(path.join(__dirname, '..', 'web', 'index.html'));
    }
  });

  // Give python server time to bind the port, then load
  setTimeout(() => {
    if (mainWindow) mainWindow.loadURL(`http://127.0.0.1:${PORT}`);
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
