; Script generated by the HM NIS Edit Script Wizard.

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "CatAtom2Osm"
!define PRODUCT_PUBLISHER "Javier S�nchez Portero"
!define PRODUCT_WEB_SITE "https://github.com/OSM-es/CatAtom2Osm"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"

; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_TEXT "El programa catatom2osm est� disponible en la terminal de comandos"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "Spanish"

; MUI end ------

Name "${PRODUCT_NAME}"
OutFile "CatAtom2Osm.exe"
InstallDir "$PROGRAMFILES\CatAtom2Osm"
ShowInstDetails show
ShowUnInstDetails show
; Check if the path entry already exists and write result to $0

Section "Principal" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File "..\CatAtom2Osm\bin\catatom2osm.bat"
  File "..\CatAtom2Osm\bin\catatom2osm.ps1"
SectionEnd

Section -Post
  EnVar::AddValue "PATH" $INSTDIR
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "La desinstalaci�n de $(^Name) finaliz� satisfactoriamente."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "�Est� completamente seguro que desea desinstalar $(^Name) junto con todos sus componentes?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  EnVar::DeleteValue "PATH" $INSTDIR
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\catatom2osm.ps1"
  Delete "$INSTDIR\catatom2osm.bat"

  RMDir "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  SetAutoClose true
SectionEnd