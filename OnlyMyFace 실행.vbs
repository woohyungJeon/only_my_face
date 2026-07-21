Option Explicit

Dim shell, folder, command, desktop, shortcutPath, shortcut
Set shell = CreateObject("WScript.Shell")
folder = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
desktop = shell.SpecialFolders("Desktop")
shortcutPath = desktop & "\Only My Face.lnk"
Set shortcut = shell.CreateShortcut(shortcutPath)
shortcut.TargetPath = WScript.ScriptFullName
shortcut.WorkingDirectory = folder
shortcut.IconLocation = folder & "\assets\only-my-face.ico,0"
shortcut.Description = "로컬 얼굴 모자이크 도구"
shortcut.Save
command = "cmd /c cd /d """ & folder & """ && pyw -3.12 app.py"
shell.Run command, 0, False
