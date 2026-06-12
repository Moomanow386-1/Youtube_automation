$env:SUPPRESS_LABEL_WARNING = "True"

$OCI     = "C:\Users\fusen\AppData\Local\Python\pythoncore-3.14-64\Scripts\oci.exe"
$SSH_KEY = "C:\Users\fusen\.oci\oci_api_key_public.pem"

$compartmentId = "ocid1.tenancy.oc1..aaaaaaaamz6u4fu67owfmc565t4i7nednmmpfvr7qffv6o3yunothxp2jdva"
$subnetId      = "ocid1.subnet.oc1.ap-singapore-1.aaaaaaaa7fxra3gkqq2eckw4q5fxzcv77y3v24ofa3uzgfk3sdzmfpr66zkq"
$imageId       = "ocid1.image.oc1.ap-singapore-1.aaaaaaaaihkypxmfxzeyjevj3eutgzlnqjazicn27goya2lpr3mdmg5to2tq"
$ad            = "zPHF:AP-SINGAPORE-1-AD-1"

Write-Host "=== Oracle ARM VM Auto-Retry ===" -ForegroundColor Cyan
Write-Host "Will retry every 2-3 minutes until capacity is available."
Write-Host ""

$attempt = 1
while ($true) {
    Write-Host "[$attempt] $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Trying..." -ForegroundColor Yellow

    $output = & $OCI compute instance launch `
        --compartment-id $compartmentId `
        --availability-domain $ad `
        --shape "VM.Standard.A1.Flex" `
        --shape-config "file://C:\Users\fusen\.oci\shape_config.json" `
        --image-id $imageId `
        --subnet-id $subnetId `
        --assign-public-ip true `
        --ssh-authorized-keys-file "C:\Users\fusen\.oci\vm_ssh_key.pub" `
        --display-name "youtube-bot" 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS! VM created!" -ForegroundColor Green
        Write-Host $output
        break
    }

    $outputStr = $output -join " "
    if ($outputStr -match "Out of host capacity") {
        Write-Host "  Out of capacity - retry" -ForegroundColor Red
    } else {
        Write-Host "  Error: $($output | Select-Object -First 3)" -ForegroundColor Red
    }

    $logEntry = @{attempt=$attempt; time=(Get-Date -Format 'HH:mm:ss'); status="failed"} | ConvertTo-Json -Compress
    Add-Content -Path "D:\All_Automation\Youtube_automation\vm_retry_log.jsonl" -Value $logEntry

    # Update vm_data.js for local HTML dashboard (no server needed)
    $lines = Get-Content "D:\All_Automation\Youtube_automation\vm_retry_log.jsonl" -ErrorAction SilentlyContinue
    if ($lines) {
        $jsArray = "[" + ($lines -join ",") + "]"
        "const VM_LOG = $jsArray;" | Set-Content "D:\All_Automation\Youtube_automation\docs\vm_data.js" -Encoding UTF8
    }

    $attempt++
    Start-Sleep -Seconds 300
}
