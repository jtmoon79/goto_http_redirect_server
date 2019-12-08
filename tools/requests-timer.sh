#!/usr/bin/env bash

set -e
set -u

if [[ ${#} != 1 ]] && [[ ${#} != 2 ]]; then
    echo "usage:

    $(basename -- "${0}") URL [COUNT]

        URL of the request
        COUNT of request processes

This script is to aid manual testing of many requests and the time elapsed.
It starts COUNT child processes that loop curl request of URL.

For each request, it prints:

    milliseconds for request,HTTP return code,[PASS|FAIL] of curl request

For example:

    913,200,PASS
" >&2
    exit 1
fi


readonly url=${1}
declare -a PIDs=()

function time_ms() {
    # epoch time in milliseconds
    echo -n "$(($(date '+%s%N') / 1000000))"
}

declare -i reqs=${2:-5}  # requestors
declare tspl=0.1  # time sleep per launch, per request

# create ${reqs} number of child process of loops of curl requests
for i in $(seq 1 ${reqs}); do
   (
        set +e
        sleep $(python -c "print(${reqs} * ${tspl} + 2);")
        declare mesg=
        while sleep ${tspl}; do
            start=$(time_ms)
            if out=$(curl -v "${url}" 2>&1); then
                mesg='PASS'
            else
                mesg='FAIL'
            fi
            end=$(time_ms)
            code=$(echo "${out}" | grep -Fe '< HTTP/1.0 ' | grep -oEe ' [[:digit:]]+ ' | tr -d ' ')
            echo "$((${end} - ${start})),${code},${mesg}"
        done
   ) &
   PIDs[${#PIDs[@]}]=$!
   sleep ${tspl}
done

function exit_() {
    (
        set -x
        #kill "${PIDs[@]}"
    )
}
trap exit_ EXIT

echo "Script PID is $$" >&2
echo "Child PIDs is ${PIDs[*]}" >&2
echo "exit via Ctrl+c" >&2
wait
