#define AppName "GameDev AI Office"
#define AppVersion "0.2.0"
[Setup]
AppId={{F03272D4-0EB9-498A-8BCB-C6972F485432}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=GameDev AI Office
DefaultDirName={localappdata}\Programs\GameDevAIOffice
DefaultGroupName=GameDev AI Office
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=GameDevAIOffice-Setup
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=GameDev AI Office

[Files]
Source: "dist\GameDevAIOffice\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GameDev AI Office"; Filename: "{app}\GameDevAIOffice.exe"
Name: "{autodesktop}\GameDev AI Office"; Filename: "{app}\GameDevAIOffice.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons"

[Run]
Filename: "{app}\GameDevAIOffice.exe"; Description: "Launch GameDev AI Office"; Flags: nowait postinstall skipifsilent
