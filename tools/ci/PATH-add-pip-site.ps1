# PATH-add-pip-site.ps1

# update PATH with potential pip install locations on a Windows host
function add_pip_site_PATH {
    # presumes $PYTHON is set to the desired python interpreter
    $usersite = & $PYTHON -c 'import site; print(site.USER_SITE);'
    $userbase = & $PYTHON -c 'import site; print(site.USER_BASE);'
    $userbasescript1 = Join-Path -Path "$userbase" -ChildPath "Script"
    # --user install location on Windows 10 is annoyingly specific and not
    # available in site module
    $userbasescript2 = Join-Path -Path "$userbase" -ChildPath (& $PYTHON -c 'import sys; print(\"Python\" + str(sys.version_info[0]) + str(sys.version_info[1]));')
    $userbasescript3 = Join-Path -Path "$userbasescript2" -ChildPath "Scripts"
    $paths = $env:PATH.Split($([IO.Path]::PathSeparator))
    ForEach ($path_ in @("$usersite",
                         "$userbase",
                         "$userbasescript1",
                         "$userbasescript2",
                         "$userbasescript3"))
    {
        if ($paths -contains $path_) {
            Write-Debug "skip adding to env:PATH '$path_'"
            continue
        }
        $env:PATH += "$([IO.Path]::PathSeparator)$path_"
        Write-Debug "added to env:PATH '$path_'"
    }
}

add_pip_site_PATH
