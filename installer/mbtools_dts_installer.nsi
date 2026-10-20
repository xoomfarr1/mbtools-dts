; ------------------------------------------------------------------
; MBTools-DTS Windows Installer
; Build: makensis mbtools_dts_installer.nsi
; Output: mbtools-dts_setup.exe
; ------------------------------------------------------------------

Name "MBTools-DTS"
OutFile "mbtools-dts_setup.exe"
Unicode true
InstallDir "$PROGRAMFILES64\MBTools-DTS"
InstallDirRegKey HKCU "Software\MBTools-DTS" "InstallDir"

!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_ICON "installer/mbtools-dts-icon.ico"
!define MUI_UNICON "installer/mbtools-dts-icon.ico"
!define MUI_HEADERIMAGE

; Version metadata (shown in Program Files / Add/Remove Programs)
VIAddVersionKey "ProductName" "MBTools-DTS"
VIAddVersionKey "CompanyName" "MBTools-DTS Contributors"
VIAddVersionKey "FileDescription" "MBTools-DTS - open-source Mercedes-Benz diagnostics"
VIAddVersionKey "ProductVersion" "1.0.0"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2026 MBTools-DTS Contributors"
VIAddVersionKey "Comments" "Open-source Mercedes-Benz diagnostics combining mbtools, DT-Monaco and the PT3G J2534 driver."

; ------------------------------------------------------------------
; Pages
; ------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ------------------------------------------------------------------
; Install section
; ------------------------------------------------------------------
Section "Install MBTools-DTS" SectionIdMain
    SetOutPath "$INSTALLDIR"

    ; The PyInstaller bundle (built by the packaging step)
    File /r "dist\mpackage.exe" "$INSTALLDIR\mpackage.exe"

    ; Shortcuts
    CreateShortcut "$SMPROGRAMS\MBTools-DTS\MBTools-DTS.lnk" "$INSTALLDIR\mpackage.exe"
    CreateShortcut "$DESKTOP\MBTools-DTS.lnk" "$INSTALLDIR\mpackage.exe"

    ; Registry entries
    WriteRegStr HKCU "Software\MBTools-DTS" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\MBTools-DTS" "ProductName" "MBTools-DTS"
    WriteRegStr HKCU "Software\MBTools-DTS" "ProductVersion" "1.0.0"

    ; Start menu folder
    SetShellVarContext current
    CreateDirectory "$SMPROGRAMS\MBTools-DTS"
    ; (shortcut already created above)
SectionEnd

Section "Uninstall" SectionIdUninst
    Delete "$DESKTOP\MBTools-DTS.lnk"
    RMDir "$SMPROGRAMS\MBTools-DTS"
    DeleteRegKey HKCU "Software\MBTools-DTS"
    Delete "$INSTALLDIR\mpackage.exe"
    RMDir "$INSTALLDIR"
SectionEnd
