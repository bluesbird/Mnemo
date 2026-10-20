#!/bin/sh
set -eu

state_dir="${HOME}/.local/state/mnemo"
mkdir -p "$state_dir"
exec 9>"$state_dir/reconcile.lock"
if ! flock -n 9; then
    printf '%s SKIP: reconciliation is already running\n' "$(date -Iseconds)"
    exit 0
fi

printf '%s Starting index reconciliation\n' "$(date -Iseconds)"
if curl --fail-with-body --silent --show-error --connect-timeout 10 --max-time 600 \
    --request POST http://127.0.0.1:8081/rag-api/api/v1/index/reconcile; then
    printf '\n%s OK: index reconciliation completed\n' "$(date -Iseconds)"
else
    status=$?
    printf '\n%s ERROR: index reconciliation failed (curl exit %s)\n' "$(date -Iseconds)" "$status" >&2
    exit "$status"
fi
