@echo off
:: Creates a Desktop shortcut for BRDC Downloader
set "TARGET=%~dp0BRDC_Downloader.bat"
set "SHORTCUT=%USERPROFILE%\Desktop\BRDC Downloader.lnk"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath = '%TARGET%'; ^
   $s.WorkingDirectory = '%~dp0'; ^
   $s.Description = 'BRDC GPS Ephemeris Downloader'; ^
   $s.Save()"

echo Desktop shortcut created: %SHORTCUT%
pause
