#!/bin/sh
set -eu

AUTH_FILE="/etc/nginx/.htpasswd"
AUTH_CONF="/etc/nginx/conf.d/auth.conf"

if [ "${PANEL_BASIC_AUTH_ENABLED:-false}" != "true" ]; then
  printf "# basic auth disabled\n" > "$AUTH_CONF"
  exit 0
fi

if [ -z "${PANEL_AUTH_USER:-}" ] || [ -z "${PANEL_AUTH_PASSWORD:-}" ]; then
  echo "PANEL_AUTH_USER and PANEL_AUTH_PASSWORD must be set when PANEL_BASIC_AUTH_ENABLED=true."
  exit 1
fi

htpasswd -bc "$AUTH_FILE" "$PANEL_AUTH_USER" "$PANEL_AUTH_PASSWORD"
chmod 640 "$AUTH_FILE"
printf "auth_basic \"Restricted SwagMonitor Panel\";\nauth_basic_user_file %s;\n" "$AUTH_FILE" > "$AUTH_CONF"
