# Run as Administrator
# Adds WakeToRun to YoutubeAutomation_Daily task

$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 1 `
    -RestartInterval (New-TimeSpan -Minutes 30)

Set-ScheduledTask -TaskName "YoutubeAutomation_Daily" -Settings $settings

$result = (Get-ScheduledTask -TaskName "YoutubeAutomation_Daily").Settings.WakeToRun
Write-Output "WakeToRun set to: $result"
if ($result) { Write-Output "SUCCESS - task will now wake PC at 9am even if sleeping" }
else { Write-Output "FAILED - still no admin rights?" }
