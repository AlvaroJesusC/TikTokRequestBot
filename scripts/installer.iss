; ==========================================================================
; INNO SETUP SCRIPT - TikTok LIVE SongBot Installer
; ==========================================================================
; Requisito: Descargar Inno Setup 6 gratis desde https://jrsoftware.org/isinfo.php
; Luego abrir este archivo .iss con Inno Setup Compiler y hacer clic en "Compile".
;
; Este script toma el TikTokRequestBot.exe de la carpeta dist/ (generado por
; PyInstaller) y lo empaqueta en un instalador profesional de Windows con:
;   - Wizard de instalación clásico de Windows
;   - Acceso directo en Escritorio y Menú Inicio
;   - Creación automática de carpetas (music/, data/cache/)
;   - Copia config.example.yaml como plantilla
;   - Desinstalador limpio
; ==========================================================================

#define MyAppName "TikTok LIVE SongBot"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AlvaroJesusC"
#define MyAppURL "https://github.com/AlvaroJesusC/TikTokRequestBot"
#define MyAppExeName "TikTokRequestBot.exe"

[Setup]
AppId={{A3D7F8E2-4B1C-4E9A-B5D6-7F8A9C0E1D2B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=..\dist
OutputBaseFilename=Setup_TikTokSongBot_v{#MyAppVersion}
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableProgramGroupPage=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el &Escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
; Ejecutable principal (generado por PyInstaller)
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Archivo de configuración de ejemplo
Source: "..\config.example.yaml"; DestDir: "{app}"; Flags: ignoreversion

; Carpeta de música con archivo README
Source: "..\music\LEEME.txt"; DestDir: "{app}\music"; Flags: ignoreversion

[Dirs]
; Crear carpetas necesarias automáticamente
Name: "{app}\music"
Name: "{app}\data"
Name: "{app}\data\cache"
Name: "{app}\data\cache\audio"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { Si no existe config.yaml, copiar el ejemplo como plantilla }
    if not FileExists(ExpandConstant('{app}\config.yaml')) then
    begin
      FileCopy(
        ExpandConstant('{app}\config.example.yaml'),
        ExpandConstant('{app}\config.yaml'),
        False
      );
    end;
  end;
end;
