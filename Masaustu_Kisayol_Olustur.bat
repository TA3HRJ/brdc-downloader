@echo off
:: Masaüstünde BRDC İndir kısayolu oluşturur
set "TARGET=%~dp0BRDC_Indir.bat"
set "SHORTCUT=%USERPROFILE%\Desktop\BRDC İndir.lnk"
set "ICON=%~dp0brdc.ico"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT%'); ^
   $s.TargetPath = '%TARGET%'; ^
   $s.WorkingDirectory = '%~dp0'; ^
   $s.Description = 'BRDC GPS Ephemeris Downloader'; ^
   $s.Save()"

echo Masaustu kisayolu olusturuldu: %SHORTCUT%
pause
