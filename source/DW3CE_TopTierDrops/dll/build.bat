@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
cl /nologo /O2 /W3 /MT /LD dw3ce_re_top_tier_drop.c /Fe:version.dll /link kernel32.lib user32.lib || exit /b 1
del /q dw3ce_re_top_tier_drop.obj version.lib version.exp 2>nul
