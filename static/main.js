const { app, BrowserWindow, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");
const { exec } = require("child_process");
const kill = require("tree-kill");

let mainWindow;
let pythonProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 1000,
    icon: path.join(__dirname, "frontend", "logo.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      enableRemoteModule: false,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "frontend", "login.html"));

  mainWindow.on("closed", () => {
    shutdownPython();
    mainWindow = null;
  });
}

function startPythonBackend() {
  const pythonExecutable = path.join(process.resourcesPath, "app.exe");

  if (fs.existsSync(pythonExecutable)) {
    pythonProcess = spawn(pythonExecutable, [], {
      windowsHide: true,
      detached: false,
      stdio: "ignore",
    });

    pythonProcess.on("close", (code) =>
      console.log(`Flask backend exited with code ${code}`)
    );
  } else {
    console.warn("⚠️ app.exe not found. Backend not started.");
  }
}

function shutdownPython() {
  const logCommand = `powershell -Command "Write-EventLog -LogName Application -Source 'IGrowBondsCalculator' -EntryType Information -EventId 1000 -Message 'Electron requested shutdown of app.exe.'"`;

  exec('taskkill /F /T /IM "app.exe"', (err) => {
    if (err) {
      console.error("❌ taskkill failed:", err);
    } else {
      console.log("✅ taskkill succeeded.");
    }
    pythonProcess = null;
  });

  exec(logCommand, (err) => {
    if (err) {
      console.error("❌ Failed to write to Event Log:", err);
    } else {
      console.log("📝 Shutdown logged to Event Viewer.");
    }
  });

  fetch("http://127.0.0.1:5001/shutdown", { method: "POST" })
    .then((res) => {
      if (res.ok) {
        console.log("✅ Flask shutdown endpoint called.");
      }
    })
    .catch(() => {
      console.warn("⚠️ Graceful shutdown failed. Forcing taskkill...");
      exec('taskkill /F /T /IM "app.exe"', (err) => {
        if (err) {
          console.error("❌ taskkill failed:", err);
        } else {
          console.log("✅ taskkill succeeded.");
        }
        pythonProcess = null;
      });
    });
}

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  shutdownPython();
  if (process.platform !== "darwin") app.quit();
});

ipcMain.on("login", (event, credentials) => {
  fetch("http://127.0.0.1:5001/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  })
    .then((response) => response.json())
    .then((data) => {
      event.reply("login-response", data);
    })
    .catch((error) => {
      console.error("IPC Login Error:", error);
      event.reply("login-response", {
        message: "Login failed. Flask not responding.",
        status: "error",
      });
    });
});

ipcMain.handle('quit-app', () => {
  app.quit();
});