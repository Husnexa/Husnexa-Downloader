; Inno Setup 6 Script for Husnexa
; Husnexa

#define MyAppName "Husnexa"
#define MyAppVersion "1.2.1"
#define MyAppPublisher "M.Husnan"
#define MyAppURL "https://github.com/husnexa/husnexa"
#define MyAppExeName "Husnexa.exe"

[Setup]
; Unique AppId for upgrade detection
AppId={{3580C0D8-C78D-4A5E-853C-25A0FEC6D127}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=M.Husnan
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\Husnexa
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer_output
OutputBaseFilename=Husnexa_Setup_v{#MyAppVersion}
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Husnexa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "native_host_chromium.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "native_host_firefox.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
; Lets the browser extension reach the helper for this Windows user
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.husnexa.host"; ValueType: string; ValueData: "{app}\native_host_chromium.json"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\com.husnexa.host"; ValueType: string; ValueData: "{app}\native_host_chromium.json"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.husnexa.host"; ValueType: string; ValueData: "{app}\native_host_chromium.json"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Mozilla\NativeMessagingHosts\com.husnexa.host"; ValueType: string; ValueData: "{app}\native_host_firefox.json"; Flags: uninsdeletekey

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Closes any running Husnexa (including a copy left running in the background with no
// window by older versions) so the new files install and the fixed version starts cleanly.
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM "Husnexa.exe"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM "Husnexa Helper.exe"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
