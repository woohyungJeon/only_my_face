Option Explicit

' Starts the bundled runtime without opening a terminal window.
Dim shell, folder, quote, exePath, scriptPath, command
Set shell = CreateObject("WScript.Shell")
folder = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
quote = Chr(34)
exePath = folder & "\runtime\pythonw.exe"
scriptPath = folder & "\app.py"
command = quote & exePath & quote & " " & quote & scriptPath & quote
shell.Run command, 0, False
