# Installs the weekly PartRevive search-loop task (Mondays 07:30, as the current user).
$repo = Split-Path -Parent $PSScriptRoot
$py = (Get-Command python).Source
$action = New-ScheduledTaskAction -Execute $py -Argument "`"$repo\scripts\seo_weekly.py`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 07:30
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
Register-ScheduledTask -TaskName "PartRevive-SEO-Weekly" -Action $action -Trigger $trigger -Settings $settings -Description "Pulls Search Console + GA4 for PartRevive, writes reports/seo/<date>.md and opens a GitHub issue (emails Jon)." -Force | Out-Null
Get-ScheduledTask -TaskName "PartRevive-SEO-Weekly" | Select-Object TaskName, State
