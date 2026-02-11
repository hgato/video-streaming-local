#!/bin/sh
set -e

sed "s|__JWT_SECRET__|${KONG_JWT_SECRET}|" /tmp/kong.yml.template > /tmp/kong.yml

exec /docker-entrypoint.sh kong docker-start
