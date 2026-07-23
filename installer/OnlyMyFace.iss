; Compile with Inno Setup 6.  build_release.ps1 creates release\OnlyMyFace-build first.
#define AppName "Only My Face"
#define AppVersion "1.1.2"
#define AppPublisher "Only My Face"
#define AppExeName "OnlyMyFace.vbs"

[Setup]
AppId={{5D0A9B39-59C7-49B9-88B6-61F8BD9C35E9}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\OnlyMyFace
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=OnlyMyFace-Setup
SetupIconFile=..\assets\only-my-face.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\assets\only-my-face.ico

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Files]
Source: "..\release\OnlyMyFace-build\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\Only My Face"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\only-my-face.ico"; Comment: "로컬 얼굴 모자이크 도구"
Name: "{group}\Only My Face"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\assets\only-my-face.ico"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Only My Face 실행"; Flags: nowait postinstall skipifsilent shellexec
