@echo off
chcp 65001 >nul
setlocal

echo ============================================================
echo  voice_cursor  --  PyInstaller 打包脚本
echo ============================================================

REM ── 检查 pyinstaller 是否已安装 ──────────────────────────────
where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] 未找到 pyinstaller，正在安装...
    pip install pyinstaller
)

REM ── 清理上次构建产物 ─────────────────────────────────────────
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

REM ── 开始打包 ─────────────────────────────────────────────────
echo [INFO] 开始打包，请稍候...
pyinstaller voice_cursor.spec

if errorlevel 1 (
    echo.
    echo [ERROR] 打包失败，请查看上方错误信息。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  打包成功！
echo  输出目录: dist\voice_cursor\
echo  主程序:   dist\voice_cursor\voice_cursor.exe
echo ============================================================
echo.
echo  分发时请将整个 dist\voice_cursor\ 文件夹打包压缩后发给用户。
echo  不能只发 voice_cursor.exe，需要整个文件夹！
echo.
pause
