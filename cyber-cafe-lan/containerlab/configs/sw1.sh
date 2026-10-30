#!/bin/bash
# CAFE-SW1: VLAN-aware bridge, equivalent of the 2960 config in packet-tracer/CAFE-SW1.txt
set -e

ip link add br0 type bridge vlan_filtering 1 vlan_default_pvid 0 stp_state 0
ip link set br0 up

# port  -> access VLAN
declare -A ACCESS=(
  [eth2]=10 [eth3]=10 [eth4]=10 [eth5]=10   # PC1-ADMIN, PC2-PC4
  [eth6]=20 [eth7]=20                       # PRINTER1-2
  [eth8]=30 [eth9]=30                       # CAM1-2
)

for port in "${!ACCESS[@]}"; do
  ethtool -K "$port" tx off >/dev/null 2>&1 || true
  ip link set "$port" master br0 up
  bridge vlan add vid "${ACCESS[$port]}" dev "$port" pvid untagged
done

# eth1 = trunk to r1, tagged 10,20,30,99
ethtool -K eth1 tx off >/dev/null 2>&1 || true
ip link set eth1 master br0 up
for vid in 10 20 30 99; do
  bridge vlan add vid "$vid" dev eth1
done

# Management SVI (VLAN 99)
bridge vlan add vid 99 dev br0 self
ip link add link br0 name vlan99 type vlan id 99
ip addr add 192.168.99.2/24 dev vlan99
ip link set vlan99 up
ip route replace default via 192.168.99.1 dev vlan99
