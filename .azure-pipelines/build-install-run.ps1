#!powershell
#
# uninstall, build, install, run
# intended for a clean Azure Pipelines environment with
# Python, pip, wheels already installed
#
# test this script in a new powershell instance with
#     Start-Process -NoNewWindow powershell .\build-install.ps1

$DebugPreference = "Continue"
$ErrorActionPreference = "Stop"
Set-PSDebug -Trace 1
 
Set-Location "$PSScriptRoot/.."

$PYTHON = 'python'
& $PYTHON --version

#
# build package
#

$PACKAGE_NAME = 'goto_http_redirect_server'
$PROGRAM_NAME = 'goto_http_redirect_server'

Push-Location '..'
& $PYTHON -m pip uninstall --yes "$PACKAGE_NAME"

# build using wheels
Pop-Location
$version = & $PYTHON -B -c 'from goto_http_redirect_server import goto_http_redirect_server as gh;print(gh.__version__)'
& $PYTHON setup.py -v bdist_wheel

# note the contents of dist
Get-ChildItem ./dist/

# get the full path to the wheel file
$cv_whl = Get-ChildItem "./dist/$PACKAGE_NAME-$version-py3-none-any.whl" -ErrorAction SilentlyContinue

& $PYTHON -m twine check $cv_whl

# install the wheel (must be done outside the project directory)
Push-Location ..
& $PYTHON -m pip install -v $cv_whl

#
# verify it runs
#

$PORT = 55923  # hopefully not in-use!
# does it run?
& $PACKAGE_NAME --version
# does it run and listen on the socket?
& $PACKAGE_NAME --debug --shutdown 2 --port $PORT --from-to '/a' 'http://foo.com'
