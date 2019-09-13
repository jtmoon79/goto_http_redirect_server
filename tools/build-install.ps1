#!powershell
#
# uninstall, build, install, run
#
# test this script in a new powershell instance with
#     Start-Process -NoNewWindow powershell .\build-install.ps1

$DebugPreference = "Continue"
$ErrorActionPreference = "Stop"
Set-PSDebug -Trace 1
 
Set-Location $PSScriptRoot

function Test-Path-Safely {
    param([string]$path)
    try {
        Test-Path $path
    } catch {
        $False
    }
}

function Get-Command-Safely {
    param([string]$command)
    try {
        Get-Command "$command" -ErrorAction SilentlyContinue
    } catch {
        $False
    }
}

#
# make a good effort to get the path to the local python 3 installation
#
Foreach ($pythonpath in @("$env:PYTHON",  # if $PTYHON is set, assume it's the PYTHON interpreter
                          'python3.7',
                          'python3.7.exe',
                          'C:\Windows\py.exe',
                          'python3',
                          'python',
                          'python.exe'))
{
    $PYTHON = Get-Command-Safely "$pythonpath" -ErrorAction SilentlyContinue
    if (($PYTHON) -and (Test-Path-Safely $PYTHON.Source)) {
        Write-Host "Found Python executable at" $PYTHON.Source
        break
    }
    $PYTHON = $null
}

# check $PYTHON runs
& $PYTHON --version

#
# build package
#

$PACKAGE_NAME = 'goto_http_redirect_server'
$PROGRAM_NAME = 'goto_http_redirect_server'

Push-Location ..

& $PYTHON -m pip uninstall --yes "$PACKAGE_NAME"

# remove previous build artifacts
Remove-Item -Recurse -Path './build/','./dist/',"./$PACKAGE_NAME.egg-info/"  -ErrorAction Ignore

# build using wheels
Pop-Location
$version = & $PYTHON -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)'
& $PYTHON setup.py -v bdist_wheel

# note the contents of dist
Get-ChildItem ./dist/

# get the full path to the wheel file
$cv_whl = Get-ChildItem "./dist/$PACKAGE_NAME-$version-py3-none-any.whl" -ErrorAction SilentlyContinue
if (-not (Test-Path-Safely $cv_whl)) {
    $cv_whl = Get-ChildItem  "./dist/$PACKAGE_NAME-$version-py3.7-none-any.whl"
}

& $PYTHON -m twine check $cv_whl

# install the wheel (must be done outside the project directory)
Push-Location ..

& $PYTHON -m pip install -v $cv_whl

& $PACKAGE_NAME --version

#
# verify it runs
#

$PORT = 55923  # hopefully not in-use!
# does it run?
& $PACKAGE_NAME --version
# does it run and listen on the socket?
& $PACKAGE_NAME --verbose --shutdown 2 --port $PORT --from-to '/a' 'http://foo.com'

#
# exit with hint
#

Write-Host "
To uninstall remaining package:

        $PYTHON -m pip uninstall -y '$PACKAGE_NAME'
"

Write-Host "Success!

To upload to pypi:

    $PYTHON -m twine upload --verbose $cv_whl
"
