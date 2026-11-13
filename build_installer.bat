@echo off
setlocal enabledelayedexpansion
title Build Windows Installer - Husnexa
cd /d "%~dp0"

echo ========================================================
echo Husnexa - Installer Build Automation
echo ========================================================
echo.

:: Prompt for version bump (P=Patch, m=Minor, M=Major, N=None) with 5-second timeout defaulting to Patch
choice /C PmMjN /CS /T 5 /D P /M "Version bump? [P]atch / [m]inor / [M]ajor / [N]one"
if errorlevel 5 (
    set "BUMP_TYPE=none"
) else if errorlevel 4 (
    set "BUMP_TYPE=major"
) else if errorlevel 3 (
    set "BUMP_TYPE=major"
) else if errorlevel 2 (
    set "BUMP_TYPE=minor"
) else (
    set "BUMP_TYPE=patch"
)

echo.
echo Selected bump type: !BUMP_TYPE!
echo.

set "SUMMARY="
set /p SUMMARY="Release summary note (optional, press Enter to skip): "

echo.
python bump_version.py !BUMP_TYPE! "!SUMMARY!"
if errorlevel 1 (
    echo.
    echo [ERROR] Version bump failed!
    pause
    exit /b 1
)

set /p CURRENT_VER=<current_version.txt
if exist current_version.txt del current_version.txt >nul 2>nul

echo.
echo ========================================================
echo Step 1/2: Building Intermediate Executable v!CURRENT_VER! (PyInstaller)...
echo ========================================================
python -m PyInstaller "Husnexa.spec" --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

if not exist "dist\Husnexa\Husnexa.exe" (
    echo.
    echo [ERROR] Expected output 'dist\Husnexa\Husnexa.exe' was not found!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo Step 2/2: Compiling Windows Installer v!CURRENT_VER! (Inno Setup 6)...
echo ========================================================

set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    goto :RunCompiler
)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    goto :RunCompiler
)
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    goto :RunCompiler
)

where ISCC.exe >nul 2>nul
if %errorlevel% equ 0 (
    set "ISCC=ISCC.exe"
    goto :RunCompiler
)

echo.
echo [ERROR] Inno Setup 6 compiler (ISCC.exe) was not found!
echo Please install Inno Setup 6 using: winget install JRSoftware.InnoSetup
pause
exit /b 1

:RunCompiler
echo Using Inno Setup compiler: "%ISCC%"
"%ISCC%" "installer.iss"
if errorlevel 1 (
    echo.
    echo [ERROR] Inno Setup installer compilation failed!
    pause
    exit /b 1
)

if not exist "installer_output\Husnexa_Setup_v!CURRENT_VER!.exe" (
    echo.
    echo [ERROR] Expected installer 'installer_output\Husnexa_Setup_v!CURRENT_VER!.exe' not found!
    pause
    exit /b 1
)

python build_extension_package.py
if errorlevel 1 (
    echo.
    echo [ERROR] Extension package build failed!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo Calculating SHA-256 Checksum...
set "SETUP_HASH="
for /f "tokens=*" %%h in ('powershell -NoProfile -Command "(Get-FileHash 'installer_output\Husnexa_Setup_v!CURRENT_VER!.exe' -Algorithm SHA256).Hash.ToLower()"') do set "SETUP_HASH=%%h"

(
    echo ## Husnexa v!CURRENT_VER!
    echo.
    echo ### 📋 Release Notes
    echo - !SUMMARY!
    echo.
    echo ### 📥 Installation
    echo Download and run **Husnexa_Setup_v!CURRENT_VER!.exe** to install or upgrade.
    echo.
    echo ---
    echo **SHA256:** `!SETUP_HASH!`
) > "installer_output\GITHUB_RELEASE_TEMPLATE_v!CURRENT_VER!.md"

echo ========================================================
echo GITHUB RELEASE READY PACK (v!CURRENT_VER!):
echo ========================================================
echo Tag Name:      v!CURRENT_VER!
echo Release Title: Husnexa v!CURRENT_VER!
echo Upload Asset:  installer_output\Husnexa_Setup_v!CURRENT_VER!.exe
echo SHA-256 Hash:  !SETUP_HASH!
echo Release Notes: installer_output\GITHUB_RELEASE_TEMPLATE_v!CURRENT_VER!.md
echo ========================================================
echo (Upload the Setup file and paste the template into GitHub Releases)
pause
