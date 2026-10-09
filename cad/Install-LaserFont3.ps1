# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Artkis
<#
.SYNOPSIS
Installs LaserFont 3 commands for the current user's AutoCAD 2023 profile.
.DESCRIPTION
Backs up replaced files before installing. Preserves existing laserfont.shx and
laserfont2.shx, drawing styles, security settings and the Startup Suite.
Does not send commands to AutoCAD or modify any open or saved drawing.
Use -WhatIf to inspect the proposed destinations without writing files.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [string] $SourceDirectory = $PSScriptRoot,
    [string] $SupportDirectory = (Join-Path $env:APPDATA 'Autodesk\AutoCAD 2023\R24.2\enu\Support'),
    [string] $BundleDirectory = (Join-Path $env:APPDATA 'Autodesk\ApplicationPlugins\LASEROUT.bundle'),
    [string] $BackupRoot = (Join-Path $env:LOCALAPPDATA 'LaserFont\backups')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$version = '3.0.2'
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Get-FullDirectory([string] $Path) {
    if ([string]::IsNullOrWhiteSpace($Path) -or $Path.Contains("`r") -or $Path.Contains("`n")) {
        throw 'An installation directory is empty or contains a line break.'
    }
    $full = [IO.Path]::GetFullPath($Path)
    if ($full -eq [IO.Path]::GetPathRoot($full)) { throw 'An installation directory cannot be a filesystem root.' }
    return $full.TrimEnd([IO.Path]::DirectorySeparatorChar)
}

function Get-BytesHash([byte[]] $Bytes) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function ConvertTo-LispPath([string] $Path) {
    return $Path.Replace('\', '/').Replace('"', '\"')
}

function Write-JsonFile([string] $Path, $Value) {
    [IO.File]::WriteAllText($Path, (($Value | ConvertTo-Json -Depth 8) + "`n"), $utf8)
}

$source = Get-FullDirectory $SourceDirectory
$support = Get-FullDirectory $SupportDirectory
$bundle = Get-FullDirectory $BundleDirectory
$contents = Join-Path $bundle 'Contents'
$backupBase = Get-FullDirectory $BackupRoot
if ($support -eq $contents) { throw 'Support and bundle Contents must be different directories.' }
foreach ($destination in @($support, $bundle)) {
    if ($backupBase -eq $destination -or $backupBase.StartsWith($destination + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'BackupRoot must be outside both installation directories.'
    }
}

# Validate every source before creating directories, backups or installed files.
$assets = @{}
foreach ($name in @('LASER3.lsp', 'laserfont3.shx', 'integration3.lsp')) {
    $path = Join-Path $source $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required source file is missing: $name" }
    $bytes = [IO.File]::ReadAllBytes($path)
    if ($bytes.Length -eq 0) { throw "Required source file is empty: $name" }
    $assets[$name] = $bytes
}

$manifestPath = Join-Path $bundle 'PackageContents.xml'
$manifest = New-Object Xml.XmlDocument
$manifest.PreserveWhitespace = $false
$manifest.XmlResolver = $null
if (Test-Path -LiteralPath $manifestPath -PathType Leaf) {
    $manifest.Load($manifestPath)
    if ($manifest.DocumentElement.LocalName -ne 'ApplicationPackage' -or $manifest.DocumentElement.GetAttribute('Name') -ne 'LASEROUT') {
        throw 'The existing bundle is not the expected LASEROUT package; nothing was changed.'
    }
} else {
    $null = $manifest.AppendChild($manifest.CreateXmlDeclaration('1.0', 'utf-8', $null))
    $packageNode = $manifest.CreateElement('ApplicationPackage')
    $null = $manifest.AppendChild($packageNode)
    $packageNode.SetAttribute('SchemaVersion', '1.0')
    $packageNode.SetAttribute('Name', 'LASEROUT')
    $packageNode.SetAttribute('Author', 'Artkis')
    $packageNode.SetAttribute('ProductType', 'Application')
    $packageNode.SetAttribute('AutodeskProduct', 'AutoCAD')
    $packageNode.SetAttribute('ProductCode', '{' + [Guid]::NewGuid().ToString().ToUpperInvariant() + '}')
}
$package = $manifest.DocumentElement
$productCode = $package.GetAttribute('ProductCode')
if ([string]::IsNullOrWhiteSpace($productCode)) { throw 'The package has no ProductCode; nothing was changed.' }
$package.SetAttribute('AppVersion', $version)
$package.SetAttribute('Description', 'LaserFont setup and LASEROUT conversion to keyed cutting polylines')

$entries = @($manifest.SelectNodes('/ApplicationPackage/Components/ComponentEntry') | Where-Object {
    $_.GetAttribute('AppName') -eq 'LASEROUT' -or $_.GetAttribute('ModuleName').Replace('\', '/') -match '(^|/)LASEROUT\.lsp$'
})
if ($entries.Count -gt 1) { throw 'Multiple LASEROUT component entries require reconciliation before installation.' }
if ($entries.Count -eq 1) {
    $entry = $entries[0]
} else {
    $components = $manifest.CreateElement('Components')
    $runtime = $manifest.CreateElement('RuntimeRequirements')
    foreach ($pair in @(@('OS','Win64'), @('Platform','AutoCAD'), @('SeriesMin','R24.2'), @('SeriesMax','R24.2'))) {
        $runtime.SetAttribute($pair[0], $pair[1])
    }
    $null = $components.AppendChild($runtime)
    $entry = $manifest.CreateElement('ComponentEntry')
    $null = $components.AppendChild($entry)
    $null = $package.AppendChild($components)
}
foreach ($pair in @(@('AppName','LASEROUT'), @('ModuleName','./Contents/LASEROUT.lsp'),
        @('PerDocument','True'), @('LoadOnCommandInvocation','True'),
        @('LoadOnAutoCADStartup','True'), @('LoadOnAppearance','False'))) {
    $entry.SetAttribute($pair[0], $pair[1])
}
foreach ($node in @($entry.SelectNodes('Commands'))) { $null = $entry.RemoveChild($node) }
$commands = @('LASEROUT','LASERFONT')
$commandNode = $manifest.CreateElement('Commands')
$commandNode.SetAttribute('GroupName', 'LASEROUT')
foreach ($command in $commands) {
    $node = $manifest.CreateElement('Command')
    $node.SetAttribute('Global', $command)
    $node.SetAttribute('Local', $command)
    $null = $commandNode.AppendChild($node)
}
$null = $entry.AppendChild($commandNode)
$xmlSettings = New-Object Xml.XmlWriterSettings
$xmlSettings.Encoding = $utf8
$xmlSettings.Indent = $true
$xmlStream = New-Object IO.MemoryStream
$xmlWriter = [Xml.XmlWriter]::Create($xmlStream, $xmlSettings)
try { $manifest.Save($xmlWriter); $xmlWriter.Flush(); $manifestBytes = $xmlStream.ToArray() }
finally { $xmlWriter.Dispose(); $xmlStream.Dispose() }

$corePath = ConvertTo-LispPath (Join-Path $support 'LASER3.lsp')
$integrationPath = ConvertTo-LispPath (Join-Path $support 'integration3.lsp')
$loader = @"
;;; LaserFont 3.0.2 demand loader. Utility code: MIT.
;;; Absolute installation paths avoid loading a different copy from a drawing folder.
(load "$corePath")
(load "$integrationPath")
(princ)
"@
$assets['LASEROUT.lsp'] = $utf8.GetBytes($loader + "`n")
$targets = @()
foreach ($location in @(@{Name='Support'; Path=$support}, @{Name='BundleContents'; Path=$contents})) {
    foreach ($name in @('LASER3.lsp','laserfont3.shx','integration3.lsp','LASEROUT.lsp')) {
        $targets += [pscustomobject]@{Path=(Join-Path $location.Path $name); Bytes=$assets[$name]; RelativeBackup=($location.Name + '\' + $name)}
    }
}
$targets += [pscustomobject]@{Path=$manifestPath; Bytes=$manifestBytes; RelativeBackup='Bundle\PackageContents.xml'}
foreach ($target in $targets) {
    if ((Test-Path -LiteralPath $target.Path) -and -not (Test-Path -LiteralPath $target.Path -PathType Leaf)) {
        throw ('An installation file path is occupied by a directory: ' + $target.Path)
    }
}

$legacy = @()
foreach ($folder in @($support, $contents)) {
    foreach ($name in @('laserfont.shx','laserfont2.shx')) {
        $path = Join-Path $folder $name
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $legacy += [pscustomobject]@{Path=$path; SHA256=(Get-BytesHash ([IO.File]::ReadAllBytes($path)))}
        }
    }
}

if (-not $PSCmdlet.ShouldProcess(($support + ' and ' + $bundle), 'Back up existing files and install LaserFont 3.0.2 with LASEROUT and LASERFONT')) {
    [pscustomobject]@{Status='NotApplied'; Version=$version; SourceDirectory=$source; SupportDirectory=$support; BundleDirectory=$bundle; FileCount=$targets.Count; Commands=$commands}
    return
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8)
$backup = Join-Path $backupBase $stamp
$null = [IO.Directory]::CreateDirectory($backup)
$records = @()
foreach ($target in $targets) {
    $existed = Test-Path -LiteralPath $target.Path -PathType Leaf
    $oldHash = $null
    $backupFile = $null
    if ($existed) {
        $previous = [IO.File]::ReadAllBytes($target.Path)
        $oldHash = Get-BytesHash $previous
        $backupFile = Join-Path $backup $target.RelativeBackup
        $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($backupFile))
        [IO.File]::WriteAllBytes($backupFile, $previous)
        if ((Get-BytesHash ([IO.File]::ReadAllBytes($backupFile))) -ne $oldHash) { throw 'Backup verification failed; installed files were not changed.' }
    }
    $records += [pscustomobject]@{Path=$target.Path; Existed=$existed; PreviousSHA256=$oldHash; BackupFile=$backupFile; InstalledSHA256=(Get-BytesHash $target.Bytes)}
}
$receipt = [ordered]@{
    Version=$version; Status='BackedUp'; CreatedAtUtc=[DateTime]::UtcNow.ToString('o');
    SourceDirectory=$source; SupportDirectory=$support; BundleDirectory=$bundle; BackupDirectory=$backup;
    ProductCode=$productCode; Commands=$commands; Files=$records; PreservedLegacyFonts=$legacy;
    RunningAutoCADModified=$false; DrawingFilesModified=$false; RegistryModified=$false;
    LiveCommandLoadingVerified=$false
}
$receiptPath = Join-Path $backup 'installation.json'
Write-JsonFile $receiptPath $receipt
$written = @()
try {
    foreach ($target in $targets) {
        $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target.Path))
        # Mark the exact path before writing so a partial write can be recovered.
        $written += $target.Path
        [IO.File]::WriteAllBytes($target.Path, $target.Bytes)
    }
    foreach ($record in $records) {
        if ((Get-BytesHash ([IO.File]::ReadAllBytes($record.Path))) -ne $record.InstalledSHA256) {
            throw ('Installed file hash mismatch: ' + [IO.Path]::GetFileName($record.Path))
        }
    }
    $readback = New-Object Xml.XmlDocument
    $readback.Load($manifestPath)
    if ($readback.DocumentElement.GetAttribute('ProductCode') -ne $productCode -or $readback.DocumentElement.GetAttribute('AppVersion') -ne $version) {
        throw 'Installed package metadata verification failed.'
    }
    foreach ($font in $legacy) {
        if ((Get-BytesHash ([IO.File]::ReadAllBytes($font.Path))) -ne $font.SHA256) { throw 'A legacy font changed unexpectedly.' }
    }
    $receipt.Status = 'Installed'
    $receipt['VerifiedAtUtc'] = [DateTime]::UtcNow.ToString('o')
    Write-JsonFile $receiptPath $receipt
} catch {
    $installationError = $_
    $rollbackErrors = @()
    foreach ($record in $records) {
        if ($written -notcontains $record.Path) { continue }
        try {
            if ($record.Existed) {
                [IO.File]::WriteAllBytes($record.Path, [IO.File]::ReadAllBytes($record.BackupFile))
                if ((Get-BytesHash ([IO.File]::ReadAllBytes($record.Path))) -ne $record.PreviousSHA256) { throw 'Restored hash mismatch.' }
            } elseif (Test-Path -LiteralPath $record.Path -PathType Leaf) {
                # Preserve newly created failed-install files rather than deleting them.
                $index = [Array]::IndexOf($records, $record)
                $quarantine = Join-Path $backup ('failed-new-' + $index + '-' + [IO.Path]::GetFileName($record.Path))
                Move-Item -LiteralPath $record.Path -Destination $quarantine
            }
        } catch { $rollbackErrors += [pscustomobject]@{Path=$record.Path; Error=$_.Exception.Message} }
    }
    $receipt.Status = if ($rollbackErrors.Count) { 'FailedRollbackIncomplete' } else { 'FailedRolledBack' }
    $receipt['Error'] = $installationError.Exception.Message
    $receipt['RollbackErrors'] = $rollbackErrors
    Write-JsonFile $receiptPath $receipt
    throw ('LaserFont installation failed. Status: ' + $receipt.Status + '. Backup receipt: ' + $receiptPath + '. ' + $installationError.Exception.Message)
}

[pscustomobject]@{
    Status='Installed'; Version=$version; VerifiedFiles=$records.Count;
    SupportDirectory=$support; BundleDirectory=$bundle; BackupDirectory=$backup; Receipt=$receiptPath;
    ProductCode=$productCode; Commands=$commands; LegacyFontsPreserved=$legacy.Count;
    LiveCommandLoadingVerified=$false;
    NextStep='Load the installed LASEROUT.lsp to refresh commands in an existing drawing, or restart AutoCAD for demand loading. No drawing was changed by this installer.'
}
