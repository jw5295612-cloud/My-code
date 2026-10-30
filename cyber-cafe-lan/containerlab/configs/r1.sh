#!/bin/bash
# CAFE-R1: router-on-a-stick + DHCP + NAT + firewall.
# Mirrors packet-tracer/CAFE-R1.txt (iptables FORWARD chain = the IOS ACLs).
set -e

ADMIN=192.168.10.10
PCS=192.168.10.0/24
PRINTERS=192.168.20.0/24
CCTV=192.168.30.0/24
MGMT=192.168.99.0/24

sysctl -qw net.ipv4.ip_forward=1 || true   # also set via clab "sysctls"
ethtool -K eth1 tx off >/dev/null 2>&1 || true
ethtool -K eth2 tx off >/dev/null 2>&1 || true
ip link set eth1 up

# --- VLAN subinterfaces on the trunk ---
for vid in 10 20 30 99; do
  ip link add link eth1 name "eth1.$vid" type vlan id "$vid"
  ip addr add "192.168.$vid.1/24" dev "eth1.$vid"
  ip link set "eth1.$vid" up
done

# --- WAN ---
ip addr add 203.0.113.2/30 dev eth2
ip link set eth2 up
ip route replace default via 203.0.113.1 dev eth2

# --- DHCP for customer PCs (VLAN 10) ---
dnsmasq --port=0 --interface=eth1.10 --bind-interfaces \
  --dhcp-range=192.168.10.11,192.168.10.254,255.255.255.0,12h \
  --dhcp-option=option:router,192.168.10.1 \
  --dhcp-option=option:dns-server,198.51.100.10 \
  --dhcp-option=option:domain-name,cybercafe.local \
  --dhcp-leasefile=/tmp/dnsmasq.leases

# --- Firewall between VLANs (default deny) ---
iptables -P FORWARD DROP
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Admin/cashier PC: CCTV + management
iptables -A FORWARD -s $ADMIN -d $CCTV -j ACCEPT
iptables -A FORWARD -s $ADMIN -d $MGMT -j ACCEPT
# Management VLAN can reach every internal VLAN
iptables -A FORWARD -s $MGMT -d 192.168.0.0/16 -j ACCEPT
# Customers -> printers (RAW 9100, LPD 515, IPP 631, ping)
iptables -A FORWARD -s $PCS -d $PRINTERS -p tcp -m multiport --dports 9100,515,631 -j ACCEPT
iptables -A FORWARD -s $PCS -d $PRINTERS -p icmp --icmp-type echo-request -j ACCEPT
# Internet: only PCs and management (printers/CCTV stay offline)
iptables -A FORWARD -i eth1.10 -o eth2 -j ACCEPT
iptables -A FORWARD -i eth1.99 -o eth2 -j ACCEPT

# --- NAT overload (PAT) ---
iptables -t nat -A POSTROUTING -o eth2 -s $PCS -j MASQUERADE
iptables -t nat -A POSTROUTING -o eth2 -s $MGMT -j MASQUERADE
