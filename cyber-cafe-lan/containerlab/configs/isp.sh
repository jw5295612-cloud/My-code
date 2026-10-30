#!/bin/bash
# ISP + "Internet": WAN peer of r1, hosts www.internet.test on 198.51.100.10
set -e

ethtool -K eth1 tx off >/dev/null 2>&1 || true
ip addr add 203.0.113.1/30 dev eth1
ip link set eth1 up
ip addr add 198.51.100.10/32 dev lo

# Public DNS for the lab
dnsmasq --listen-address=198.51.100.10 --bind-interfaces --no-resolv --no-hosts \
  --address=/www.internet.test/198.51.100.10

# Public web server
mkdir -p /srv/www
echo "Welcome to the Internet (served by the ISP lab node)" > /srv/www/index.html
setsid busybox httpd -f -p 198.51.100.10:80 -h /srv/www >/dev/null 2>&1 < /dev/null &
