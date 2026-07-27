Unicode True

!include "MUI2.nsh"

!define APP_NAME "Macro Recorder JSON"
!define APP_VERSION "3.1.0"
!define APP_PUBLISHER "Pizzaroles"
!define APP_EXE "MacroRecorderJSON.exe"
!define APP_UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MacroRecorderJSON"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "..\dist\Macro-Recorder-JSON-Setup-${APP_VERSION}.exe"
InstallDir "$LOCALAPPDATA\Programs\Macro Recorder JSON"
InstallDirRegKey HKCU "Software\MacroRecorderJSON" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "${APP_NAME}"

VIProductVersion "3.1.0.0"
VIAddVersionKey /LANG=1033 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1033 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=1033 "FileDescription" "${APP_NAME} installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_PARAMETERS "--strategy --language es"
!define MUI_FINISHPAGE_RUN_TEXT "Abrir Estrategia grabada"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "English"

Section "Macro Recorder JSON" MainSection
  SectionIn RO
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File /r "..\dist\MacroRecorderJSON\*.*"

  WriteRegStr HKCU "Software\MacroRecorderJSON" "InstallDir" "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\Macro Recorder JSON"
  CreateShortcut "$SMPROGRAMS\Macro Recorder JSON\Macro Recorder JSON.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\Macro Recorder JSON\Automation Studio.lnk" "$INSTDIR\${APP_EXE}" "--automation --language es"
  CreateShortcut "$SMPROGRAMS\Macro Recorder JSON\Estrategia grabada.lnk" "$INSTDIR\${APP_EXE}" "--strategy --language es"
  CreateShortcut "$SMPROGRAMS\Macro Recorder JSON\Desinstalar.lnk" "$INSTDIR\Uninstall.exe"

  CreateShortcut "$DESKTOP\Macro Recorder JSON.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$DESKTOP\Automation Studio.lnk" "$INSTDIR\${APP_EXE}" "--automation --language es"
  CreateShortcut "$DESKTOP\Estrategia grabada.lnk" "$INSTDIR\${APP_EXE}" "--strategy --language es"

  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${APP_UNINSTALL_KEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${APP_UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${APP_UNINSTALL_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\Macro Recorder JSON.lnk"
  Delete "$DESKTOP\Automation Studio.lnk"
  Delete "$DESKTOP\Estrategia grabada.lnk"
  RMDir /r "$SMPROGRAMS\Macro Recorder JSON"

  DeleteRegKey HKCU "${APP_UNINSTALL_KEY}"
  DeleteRegKey HKCU "Software\MacroRecorderJSON"

  RMDir /r "$INSTDIR"

  ; Personal macros, profiles, and preferences are intentionally preserved in
  ; LocalAppData so uninstalling or upgrading cannot erase user work.
SectionEnd
