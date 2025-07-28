@echo off
setlocal enabledelayedexpansion
set "subtitle=<p style='color:#666;font-style:italic;'>Learn English By Quotes and Wisdom</p>"

for /f "delims=" %%f in ('dir /b docs\quotes\*.html') do (
    echo Processing %%f
    (
        for /f "usebackq delims=" %%l in ("docs\quotes\%%f") do (
            echo %%l
            echo %%l | findstr /i "<h1" >nul && echo !subtitle!
        )
    ) > "docs\quotes\%%f.tmp"
    move /y "docs\quotes\%%f.tmp" "docs\quotes\%%f" >nul
)

echo.
echo Subtitles successfully added to all files!
pause