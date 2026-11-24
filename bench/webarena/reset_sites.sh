#!/usr/bin/env bash
# Reset the stateful WebArena sites on diffuspace by recreating each container
# from its image, then reapplying the localhost configuration. Map and
# Wikipedia are read-only and are left alone.
# Usage: reset_sites.sh [shopping] [shopping-admin] [forum] [gitlab]   (default: all four)
set -euo pipefail
sites=("$@")
[ ${#sites[@]} -eq 0 ] && sites=(shopping shopping-admin forum gitlab)

wait_http() {  # url, timeout seconds
  local deadline=$((SECONDS + $2))
  until curl -s -o /dev/null -m 10 -w '%{http_code}' "$1" | grep -qE '^(200|302)$'; do
    [ $SECONDS -gt $deadline ] && { echo "timeout waiting for $1" >&2; return 1; }
    sleep 5
  done
}

wait_mysql() {  # container
  local deadline=$((SECONDS + 300))
  until podman exec "$1" mysql -u magentouser -pMyPassword magentodb -e 'SELECT 1' >/dev/null 2>&1; do
    [ $SECONDS -gt $deadline ] && { echo "timeout waiting for mysql in $1" >&2; return 1; }
    sleep 5
  done
}

magento() {  # container, port, admin settings (0/1)
  local c=$1 port=$2 admin=$3 m=/var/www/magento2/bin/magento
  wait_mysql "$c"
  podman exec "$c" php $m setup:store-config:set --base-url="http://localhost:$port" >/dev/null
  podman exec "$c" mysql -u magentouser -pMyPassword magentodb -e \
    "UPDATE core_config_data SET value='http://localhost:$port/' WHERE path = 'web/secure/base_url';"
  if [ "$admin" = 1 ]; then
    podman exec "$c" php $m config:set admin/security/password_is_forced 0 >/dev/null
    podman exec "$c" php $m config:set admin/security/password_lifetime 0 >/dev/null
  fi
  podman exec "$c" php $m cache:flush >/dev/null
}

recreate() {  # name, run args...
  local name=$1; shift
  echo "$(date +%T) resetting $name"
  podman rm -f "$name" >/dev/null
  podman run --name "$name" -d "$@" >/dev/null
}

for s in "${sites[@]}"; do
  case $s in
    shopping)
      recreate webarena-shopping -p 127.0.0.1:7770:80 localhost/shopping_final_0712
      magento webarena-shopping 7770 0
      wait_http http://localhost:7770 300 ;;
    shopping-admin)
      recreate webarena-shopping-admin -p 127.0.0.1:7780:80 localhost/shopping_admin_final_0719
      magento webarena-shopping-admin 7780 1
      wait_http http://localhost:7780/admin 300 ;;
    forum)
      recreate webarena-forum -p 127.0.0.1:9999:80 localhost/postmill-populated-exposed-withimg
      wait_http http://localhost:9999 300 ;;
    gitlab)
      recreate webarena-gitlab -p 127.0.0.1:8023:8023 localhost/gitlab-populated-final-port8023 \
        /opt/gitlab/embedded/bin/runsvdir-start
      sleep 10
      podman exec webarena-gitlab sed -i "s|^external_url.*|external_url 'http://localhost:8023'|" /etc/gitlab/gitlab.rb
      podman exec webarena-gitlab gitlab-ctl reconfigure >/dev/null
      wait_http http://localhost:8023/explore 900 ;;
    *) echo "unknown site $s" >&2; exit 2 ;;
  esac
  echo "$(date +%T) $s ready"
done
