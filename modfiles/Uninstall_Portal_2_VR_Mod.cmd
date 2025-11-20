@ECHO OFF

:choice
set /P c=Are you sure you want to uninstall Portal 2 VR Mod [Y/N]?
if /I "%c%" EQU "Y" goto :removemod
if /I "%c%" EQU "N" goto :donotremove
goto :choice

:removemod

echo Uninstalling...
del /Q ".\bin\d3d9.dll"
del /Q ".\bin\openvr_api.dll"
RD /Q /S ".\portal2_dlc3"
RD /Q /S ".\VR"
echo Portal 2 VR Mod is uninstalled.
pause
exit

:donotremove
echo Portal 2 VR Mod will not be uninstalled. Please run this program again if you wish to uninstall.
pause
exit