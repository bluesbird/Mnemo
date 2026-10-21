#!/bin/sh
set -eu

: "${UI_KNOWLEDGE_UPSTREAM:=http://knowledge-service:8080}"
: "${UI_RAG_UPSTREAM:=http://rag-service:8000}"
: "${UI_RATE_LIMITS:=off}"

# Only origins, not paths or nginx syntax. Render only these variables.
for upstream in "$UI_KNOWLEDGE_UPSTREAM" "$UI_RAG_UPSTREAM"; do
    if ! printf '%s\n' "$upstream" | grep -Eq '^https?://[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?(:[0-9]{1,5})?$'; then
        echo "Invalid UI upstream: expected an http(s) hostname origin with optional port." >&2
        exit 1
    fi
    case "$upstream" in
        *'
'*) echo "Invalid UI upstream: newline." >&2; exit 1 ;;
    esac
done

case "$UI_RATE_LIMITS" in
    on|off) ;;
    *) echo "Invalid UI_RATE_LIMITS: expected on or off." >&2; exit 1 ;;
esac

export UI_KNOWLEDGE_UPSTREAM UI_RAG_UPSTREAM UI_RATE_LIMITS
umask 077
envsubst '${UI_KNOWLEDGE_UPSTREAM} ${UI_RAG_UPSTREAM} ${UI_RATE_LIMITS}' \
    < /opt/mnemo/default.conf.template > /etc/nginx/conf.d/default.conf
chmod 600 /etc/nginx/conf.d/default.conf
nginx -t
exec "$@"
