param(
    [ValidateSet("api", "worker")]
    [string]$Mode = "api",

    [string]$Namespace = "transfer-system",

    [switch]$SkipLogs
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if ($Mode -eq "api") {
    $jobName = "transfer-api-load"
    $manifest = Join-Path $root "k8s/load-api-job.yaml"
} else {
    $jobName = "transfer-worker-load"
    $manifest = Join-Path $root "k8s/load-worker-job.yaml"
}

Write-Host "Recreating Kubernetes Job: $jobName"
kubectl delete job $jobName --namespace $Namespace --ignore-not-found=true
kubectl apply --namespace $Namespace -f $manifest

Write-Host ""
Write-Host "Watch scaling in another terminal:"
Write-Host "  kubectl get hpa transfer-app-hpa --namespace $Namespace --watch"
Write-Host "  kubectl get scaledobject transfer-worker-scaledobject --namespace $Namespace --watch"
Write-Host "  kubectl get pods --namespace $Namespace --watch"
Write-Host ""

if (-not $SkipLogs) {
    Write-Host "Waiting for the load pod to start..."
    kubectl wait --namespace $Namespace --for=condition=Ready pod -l job-name=$jobName --timeout=120s

    Write-Host "Streaming load job logs..."
    kubectl logs --namespace $Namespace -f job/$jobName
}
