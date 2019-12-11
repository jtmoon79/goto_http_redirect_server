#!powershell
#
# uninstall, build, install, run
# intended for a clean Azure Pipelines environment
#
# test this script in a new powershell instance with
#     Start-Process -NoNewWindow powershell .\build.ps1

$DebugPreference = "Continue"
$ErrorActionPreference = "Stop"
Set-PSDebug -Trace 1

# dump much information about the Azure Pipelines environment
HOSTNAME.EXE
Get-Location
try {
    Print-Env
} catch {
    Get-ChildItem env:  # fallback
}
#Get-CimInstance Win32_OperatingSystem | Select-Object $Properties | Format-Table -AutoSize

$PYTHON = 'python'

& docker info
& $PYTHON --version
& pip --version
& pip list -vvv
 
Set-Location "$PSScriptRoot/.."

& $PYTHON -m pip install --quiet --upgrade pip
& $PYTHON -m pip install --quiet --user twine
& $PYTHON -m pip list -vvv

#
# build package
#

$PACKAGE_NAME = 'goto_http_redirect_server'

# build using wheels
$version = & $PYTHON -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)'
& $PYTHON setup.py -v bdist_wheel

# note the contents of dist
Get-ChildItem ./dist/

# get the full path to the wheel file
$cv_whl = Get-ChildItem "./dist/$PACKAGE_NAME-$version-py3-none-any.whl" -ErrorAction SilentlyContinue

& $PYTHON -m twine --version
& $PYTHON -m twine check $cv_whl




Get-ChildItem "./dist/"  # REMOVE
