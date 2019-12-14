# PATH-add-pip-site.sh
#
# source this file from bash

# update PATH with potential pip install locations
function add_pip_site_PATH () {
    declare usersite=
    declare userbase=
    declare userbasebin=
    usersite=$(python -B -c 'import site; print(site.USER_SITE);')
    userbase=$(python -B -c 'import site; print(site.USER_BASE);')
    userbasebin=${userbase}/bin  # --user install location on Ubuntu
    declare path=
    for path in "${usersite}" "${userbase}" "${userbasebin}"; do
        export PATH="${PATH}:${path}"
        echo "added to PATH '${path}'" >&2
    done
}

add_pip_site_PATH
