# PowerShell script to zip the material_to_glsl_addon folder
# This script creates a zip file containing the entire folder structure

# Get the current script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define paths
$sourceFolder = Join-Path $scriptDir "material_to_glsl_addon"
$zipFileName = "material_to_glsl_addon.zip"
$zipPath = Join-Path $scriptDir $zipFileName

# Check if source folder exists
if (-not (Test-Path $sourceFolder)) {
    Write-Error "Source folder '$sourceFolder' does not exist!"
    exit 1
}

# Remove existing zip file if it exists
if (Test-Path $zipPath) {
    Write-Host "Removing existing zip file: $zipFileName"
    Remove-Item $zipPath -Force
}

# Create the zip file
Write-Host "Creating zip file: $zipFileName"
Write-Host "Source folder: $sourceFolder"

try {
    # Use .NET compression to create the zip
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    
    # Create a temporary directory to hold the folder structure we want
    $tempDir = Join-Path $env:TEMP "material_to_glsl_addon_temp"
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    
    # Copy the entire folder to temp directory
    $tempAddonDir = Join-Path $tempDir "material_to_glsl_addon"
    Copy-Item $sourceFolder $tempAddonDir -Recurse -Force
    
    # Create the zip from the temp directory (this will include the folder itself)
    [System.IO.Compression.ZipFile]::CreateFromDirectory($tempDir, $zipPath)
    
    # Clean up temp directory
    Remove-Item $tempDir -Recurse -Force
    
    Write-Host "Successfully created: $zipPath" -ForegroundColor Green
    
    # Display zip contents for verification
    Write-Host "`nZip contents:" -ForegroundColor Yellow
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    $zip.Entries | ForEach-Object { Write-Host "  $($_.FullName)" }
    $zip.Dispose()
    
} catch {
    Write-Error "Failed to create zip file: $($_.Exception.Message)"
    exit 1
}

Write-Host "`nZip file created successfully!" -ForegroundColor Green
