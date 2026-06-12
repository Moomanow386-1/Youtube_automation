# Run this once to register the daily YouTube automation task
$python = "C:\Users\fusen\AppData\Local\Python\pythoncore-3.14-64\python.exe"
$script = "C:\Users\fusen\Desktop\Youtube_automation\auto_daily.py"
$workdir = "C:\Users\fusen\Desktop\Youtube_automation"

$action = New-ScheduledTaskAction `
    -Execute $python `
    -Argument $script `
    -WorkingDirectory $workdir

$trigger = New-ScheduledTaskTrigger -Daily -At "09:00AM"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

Register-ScheduledTask `
    -TaskName "YoutubeAutomation_Daily" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Highest `
    -Description "Generate and upload 1 YouTube video daily" `
    -Force

Write-Host "Task registered! Runs daily at 9:00 AM"
Write-Host "StartWhenAvailable = ON (will run even if 9am was missed)"
