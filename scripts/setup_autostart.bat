@echo off
schtasks /create /tn "OracleVMRetry" /tr "powershell.exe -NoProfile -WindowStyle Hidden -File \"D:\All_Automation\Youtube_automation\create_vm.ps1\"" /sc onlogon /rl highest /f
if %errorlevel%==0 (
    echo SUCCESS: Task created. Script will auto-start on next login.
) else (
    echo FAILED: Run this file as Administrator.
)
pause
