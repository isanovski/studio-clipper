; kredit-isanovski: Template oleh Isanovski Saputra (@isanovskisaputra) — https://isanovskisaputra.biz.id · Lisensi Nonkomersial Isanovski Studio 1.0
; Installer Windows Isanovski Studio (Inno Setup 6). Dipanggil oleh bangun-windows.ps1.
; AppId TIDAK BOLEH diganti: dengan AppId yang sama, installer versi baru otomatis jadi wizard "perbarui"
; (folder sama, pintasan sama, hasil kerja di %USERPROFILE%\Isanovski Studio tidak disentuh).

#ifndef BahasaIsl
  #define BahasaIsl "compiler:Languages\Indonesian.isl"
#endif
#ifndef Versi
  #define Versi "0.0.0"
#endif

[Setup]
AppId={{6E1B6C2A-4D57-4F0B-9B4E-5A11C1A0D909}
AppName=Isanovski Studio
AppVersion={#Versi}
AppVerName=Isanovski Studio {#Versi}
AppPublisher=Isanovski Saputra (@isanovskisaputra)
AppPublisherURL=https://isanovskisaputra.biz.id
DefaultDirName={localappdata}\Programs\Isanovski Studio
DefaultGroupName=Isanovski Studio
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
CloseApplications=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=Pasang-Studio-Isanovski-{#Versi}-windows
SetupIconFile={#Alat}\studio\aset\ikon.ico
UninstallDisplayIcon={app}\alat\studio\aset\ikon.ico
LicenseFile={#Alat}\LISENSI.md
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "id"; MessagesFile: "{#BahasaIsl}"

[Messages]
id.WelcomeLabel2=Ini akan memasang [name/ver] di komputermu.%n%nKalau versi lama sudah terpasang, installer ini memperbaruinya. Hasil kerjamu tidak terhapus.

[Tasks]
Name: "desktop"; Description: "Buat pintasan di Desktop"; GroupDescription: "Pintasan:"

[InstallDelete]
; bersihkan paket & alat versi lama sebelum menyalin yang baru (data pengguna ada di folder lain)
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\alat"

[Files]
Source: "{#Stage}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Isanovski Studio"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\alat\studio\studio.py"""; WorkingDir: "{app}\alat\studio"; IconFilename: "{app}\alat\studio\aset\ikon.ico"
Name: "{autodesktop}\Isanovski Studio"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\alat\studio\studio.py"""; WorkingDir: "{app}\alat\studio"; IconFilename: "{app}\alat\studio\aset\ikon.ico"; Tasks: desktop

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\alat\studio\studio.py"""; WorkingDir: "{app}\alat\studio"; Description: "Buka Isanovski Studio sekarang"; Flags: nowait postinstall skipifsilent
