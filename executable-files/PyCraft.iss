#define MyAppName "PyCraft"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OOMrConrado"
#define MyAppURL "https://github.com/OOMrConrado/PyCraft"
#define MyAppExeName "PyCraft.exe"
[Setup]
AppId={{B8E9F3A1-2D4C-4E8B-9F1A-6C7D8E9F0A1B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=PyCraft-Setup
SetupIconFile=..\PyCraft-Files\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
MinVersion=10.0.17763
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
DisableWelcomePage=no
LicenseFile=..\LICENSE
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
[Files]
Source: "dist\PyCraft.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PyCraft-Files\*"; DestDir: "{app}\PyCraft-Files"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\PyCraft-Files\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\PyCraft-Files\icon.ico"; Tasks: desktopicon
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
[Code]
// Check if app is running and close it before update
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
ResultCode: Integer;
begin
// Try to close PyCraft if it's running
Exec('taskkill', '/F /IM PyCraft.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
Result := '';
end;
// Custom messages for silent update mode
function InitializeSetup(): Boolean;
begin
Result := True;
// If running in silent mode (for auto-update), don't show anything
if WizardSilent then
begin
Log('Running in silent update mode');
end;
end;
