#!/bin/sh
set -eu

: "${UI_MS1_UPSTREAM:=http://ms1-knowledge-service:8080}"
: "${UI_MS2_UPSTREAM:=http://ms2-rag-service:8000}"

# Only origins, not paths or nginx syntax. Render only these variables.
for upstream in "$UI_MS1_UPSTREAM" "$UI_MS2_UPSTREAM"; do
    if ! printf '%s\n' "$upstream" | grep -Eq '^https?://[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?(:[0-9]{1,5})?$'; then
        echo "Invalid UI upstream: expected an http(s) hostname origin with optional port." >&2
        exit 1
    fi
    case "$upstream" in
        *'
'*) echo "Invalid UI upstream: newline." >&2; exit 1 ;;
    esac
done

export UI_MS1_UPSTREAM UI_MS2_UPSTREAM
umask 077
envsubst '${UI_MS1_UPSTREAM} ${UI_MS2_UPSTREAM}' \
    < /opt/mnemo/default.conf.template > /etc/nginx/conf.d/default.conf
chmod 600 /etc/nginx/conf.d/default.conf
nginx -t
exec "$@"
