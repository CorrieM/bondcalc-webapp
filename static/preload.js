const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  sendLoginData: (data) => ipcRenderer.send("login", data),
  receiveLoginResponse: (callback) =>
    ipcRenderer.on("login-response", (_event, response) => callback(response)),
});
contextBridge.exposeInMainWorld("electronAPI", {
  quitApp: () => ipcRenderer.invoke("quit-app")
});