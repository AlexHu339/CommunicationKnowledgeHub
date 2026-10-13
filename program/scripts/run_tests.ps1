$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot\..\..").Path
$env:CKH_ROOT=$root
$env:PYTHONPATH="$root\program\backend"
& "$root\runtime\python\Scripts\python.exe" "$root\program\scripts\validate_content.py"
& "$root\runtime\python\Scripts\python.exe" -m pytest "$root\program\tests" -q
Push-Location "$root\program\frontend"
try { npm run build } finally { Pop-Location }

