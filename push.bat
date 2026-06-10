@echo off
echo ===================================================
echo  Sanae Omikuji Bot GitHub Upload Script
echo ===================================================
echo.

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Git is not installed or not in PATH.
    pause
    exit /b 1
)

if not exist .git (
    echo Initializing Git repository...
    git init
    git branch -M main
)

git remote remove origin >nul 2>nul
git remote add origin https://github.com/ankakepizza551/sanae_omikuji_bot.git
echo Remote origin set to:
echo https://github.com/ankakepizza551/sanae_omikuji_bot.git
echo.

echo Staging files...
git add .

set "commit_msg=Sanae Omikuji Bot Implementation"
echo.
echo Enter commit message (press Enter for default: Sanae Omikuji Bot Implementation):
set /p "user_msg=Message: "
if not "%user_msg%"=="" set "commit_msg=%user_msg%"

echo.
echo Committing...
git commit -m "%commit_msg%"

echo.
echo Pushing to GitHub (main branch)...
git push -u origin main

echo.
if %errorlevel% neq 0 (
    echo [ERROR] Push failed. Check your GitHub credentials.
) else (
    echo ===================================================
    echo  Upload successful!
    echo ===================================================
)
echo.
pause
