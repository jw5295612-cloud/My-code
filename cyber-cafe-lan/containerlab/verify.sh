#!/bin/bash
# Policy checks for the running cybercafe lab. Run after `containerlab deploy`.
LAB=clab-cybercafe
pass=0; fail=0

check() {  # check <expect ok|blocked> <node> <description> <command...>
  local expect=$1 node=$2 desc=$3; shift 3
  if docker exec "$LAB-$node" timeout 5 "$@" >/dev/null 2>&1; then got=ok; else got=blocked; fi
  if [ "$got" = "$expect" ]; then
    printf '  PASS  %-10s %s\n' "$node" "$desc"; pass=$((pass+1))
  else
    printf '  FAIL  %-10s %s (expected %s, got %s)\n' "$node" "$desc" "$expect" "$got"; fail=$((fail+1))
  fi
}

echo "DHCP leases on VLAN 10:"
for pc in pc2 pc3 pc4; do
  printf '  %-4s %s\n' "$pc" "$(docker exec $LAB-$pc ip -4 -o addr show eth1 | awk '{print $4}')"
done
echo

echo "Customer PCs"
check ok      pc2 "gateway reachable"            ping -c1 -W2 192.168.10.1
check ok      pc2 "Internet by name (DNS+NAT)"   curl -sf http://www.internet.test
check ok      pc3 "print to PRINTER1 :9100"      sh -c 'echo test-job | nc -N -w2 192.168.20.10 9100'
check ok      pc4 "ping PRINTER2"                ping -c1 -W2 192.168.20.11
check blocked pc2 "printer admin page :80"       nc -z -w2 192.168.20.10 80
check blocked pc3 "CCTV CAM1 web :80"            curl -sf http://192.168.30.10
check blocked pc4 "ping CAM2"                    ping -c1 -W2 192.168.30.11
check blocked pc2 "switch management"            ping -c1 -W2 192.168.99.2

echo "Admin / cashier PC"
check ok      pc1-admin "CCTV CAM1 live view"    curl -sf http://192.168.30.10
check ok      pc1-admin "CCTV CAM2 live view"    curl -sf http://192.168.30.11
check ok      pc1-admin "switch management"      ping -c1 -W2 192.168.99.2
check ok      pc1-admin "Internet"               curl -sf http://www.internet.test

echo "Printers and cameras (no Internet, no lateral access)"
check blocked printer1 "Internet"                ping -c1 -W2 198.51.100.10
check blocked cam1     "Internet"                ping -c1 -W2 198.51.100.10
check blocked cam2     "reach customer PC2"      ping -c1 -W2 "$(docker exec $LAB-pc2 ip -4 -o addr show eth1 | awk '{print $4}' | cut -d/ -f1)"
check blocked printer2 "reach CCTV"              ping -c1 -W2 192.168.30.10

echo
echo "Result: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
