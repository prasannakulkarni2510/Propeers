@echo off
REM Re-mint pacos\PACOS.exe after a dev session. See docs/adr/0004.
REM Usage: double-click, or run `build_exe.bat` from the pacos folder.
setlocal
cd /d "%~dp0"

echo [1/3] Building frontend...
pushd frontend
call npm run build
if errorlevel 1 (popd & echo FRONTEND BUILD FAILED & exit /b 1)
popd

echo [2/3] Freezing PACOS.exe (takes a few minutes)...
.venv\Scripts\pyinstaller.exe --noconfirm --onefile --name PACOS --paths src ^
  --add-data "frontend/dist;frontend_dist" ^
  --collect-all langgraph --collect-all uvicorn ^
  --collect-data googleapiclient ^
  --hidden-import backend --hidden-import pacos ^
  launcher.py
if errorlevel 1 (echo PYINSTALLER FAILED & exit /b 1)

echo [3/3] Moving exe into the workspace...
move /y dist\PACOS.exe PACOS.exe >nul
echo.
echo Done: %~dp0PACOS.exe
endlocal
