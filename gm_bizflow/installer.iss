#define MyAppName "GM BizFlow"
#define MyAppVersion "1.0.0"
#define MyAppExeName "GM_BizFlow.exe"
[Setup]
AppId={{E07DC916-52A3-4F74-A1F7-4BC70BF0E329}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=GM
DefaultDirName={autopf}\GM BizFlow
DefaultGroupName=GM BizFlow
OutputDir=installer_output
OutputBaseFilename=GM_BizFlow_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{autoprograms}\GM BizFlow"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\GM BizFlow"; Filename: "{app}\{#MyAppExeName}"
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch GM BizFlow"; Flags: nowait postinstall skipifsilent
