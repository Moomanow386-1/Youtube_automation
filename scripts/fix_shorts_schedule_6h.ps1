# Run as Administrator
# Changes YoutubeAutomation_ShortsDaily to upload every 6 hours (06:00, 12:00, 18:00, 00:00)
# Also adds WakeToRun

$taskName = "YoutubeAutomation_ShortsDaily"
$existing = Get-ScheduledTask -TaskName $taskName

$t1 = New-ScheduledTaskTrigger -Daily -At "00:00"
$t2 = New-ScheduledTaskTrigger -Daily -At "06:00"
$t3 = New-ScheduledTaskTrigger -Daily -At "12:00"
$t4 = New-ScheduledTaskTrigger -Daily -At "18:00"

$settings = New-ScheduledTaskSettingsSet `
    -WakeToRun `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Set-ScheduledTask -TaskName $taskName -Trigger $t1,$t2,$t3,$t4 -Settings $settings

Write-Output ""
Write-Output "Updated triggers:"
(Get-ScheduledTask -TaskName $taskName).Triggers | ForEach-Object {
    Write-Output "  - $($_.StartBoundary)"
}
$info = Get-ScheduledTaskInfo -TaskName $taskName
Write-Output "Next run: $($info.NextRunTime)"
Write-Output "WakeToRun: $((Get-ScheduledTask -TaskName $taskName).Settings.WakeToRun)"
Write-Output ""
Write-Output "SUCCESS - Shorts will now upload 4x/day (00:00, 06:00, 12:00, 18:00)"
