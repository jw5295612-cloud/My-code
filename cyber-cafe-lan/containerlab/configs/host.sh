#!/bin/bash
# End device bootstrap.
#   host.sh dhcp
#   host.sh static <ip/prefix> <gateway> [printer|camera]
set -e

MODE=$1
ethtool -K eth1 tx off >/dev/null 2>&1 || true
ip link set eth1 up

# Containerlab's default route points at the management network (eth0);
# lab traffic must go through the cafe router instead.
ip route del default 2>/dev/null || true

if [ "$MODE" = "dhcp" ]; then
  udhcpc -i eth1 -q -n -t 10 -T 2
else
  ip addr add "$2" dev eth1
  ip route add default via "$3" dev eth1
  echo "nameserver 198.51.100.10" > /etc/resolv.conf
fi

case "$4" in
  printer)
    # JetDirect-style RAW print server: jobs sent to TCP 9100 land in /var/spool/print.log
    mkdir -p /var/spool
    setsid socat TCP-LISTEN:9100,fork,reuseaddr \
      OPEN:/var/spool/print.log,creat,append >/dev/null 2>&1 < /dev/null &
    ;;
  camera)
    # Stand-in for the camera's web/snapshot interface on TCP 80
    mkdir -p /srv/www
    echo "CCTV $(hostname) - live view" > /srv/www/index.html
    setsid busybox httpd -f -p 80 -h /srv/www >/dev/null 2>&1 < /dev/null &
    ;;
esac
