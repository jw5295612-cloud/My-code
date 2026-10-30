# Cyber Cafe LAN: 4 PCs, 2 Printers, 2 CCTV Cameras

A small, segmented LAN for a cyber cafe, delivered two ways:

| Folder | Tool | What you get |
|---|---|---|
| [`packet-tracer/`](packet-tracer/) | Cisco Packet Tracer | Step-by-step build guide plus paste-ready IOS configs. Save the result as `CyberCafe-LAN.pkt` |
| [`containerlab/`](containerlab/) | Containerlab | A runnable lab of the same design (Linux nodes) with an automated policy test |

> **Why no `.pkt` file is committed:** `.pkt` is Packet Tracer's proprietary,
> encrypted format and can only be written reliably by Packet Tracer itself.
> The build guide gets you from a blank workspace to the finished `.pkt` in
> about 10 minutes, using the exact configs in this folder.

## Topology

```
                     INTERNET
                        |
              [ ISP ]  198.51.100.0/24  (INTERNET-SRV 198.51.100.10: web + DNS)
                        | 203.0.113.1
                        |  WAN /30
                        | 203.0.113.2  G0/1
                  +-------------+
                  |   CAFE-R1   |  Cisco 2911: router-on-a-stick, DHCP, NAT/PAT, ACLs
                  +-------------+
                        | G0/0  802.1Q trunk (VLANs 10,20,30,99; native 999)
                        | G0/1
                  +-------------+
                  |  CAFE-SW1   |  Cisco 2960-24TT  (mgmt SVI 192.168.99.2)
                  +-------------+
   Fa0/1   Fa0/2  Fa0/3  Fa0/4     Fa0/5     Fa0/6     Fa0/7   Fa0/8
     |       |      |      |         |         |         |       |
 [PC1-ADMIN][PC2] [PC3] [PC4]  [PRINTER1][PRINTER2]   [CAM1]  [CAM2]
 \________ VLAN 10 ________/   \____ VLAN 20 ____/   \_ VLAN 30 _/
```

## VLANs and IP addressing

| VLAN | Name | Subnet | Gateway (CAFE-R1) | Devices |
|---|---|---|---|---|
| 10 | CUSTOMER-PCS | 192.168.10.0/24 | 192.168.10.1 | PC1-ADMIN `.10` (static), PC2–PC4 via DHCP `.11–.254` |
| 20 | PRINTERS | 192.168.20.0/24 | 192.168.20.1 | PRINTER1 `.10`, PRINTER2 `.11` |
| 30 | CCTV | 192.168.30.0/24 | 192.168.30.1 | CAM1 `.10`, CAM2 `.11` |
| 99 | MANAGEMENT | 192.168.99.0/24 | 192.168.99.1 | CAFE-SW1 `.2` |
| 999 | NATIVE-UNUSED | — | — | Trunk native VLAN and parked unused ports |
| WAN | — | 203.0.113.0/30 | ISP `.1` | CAFE-R1 G0/1 `.2` |

PC1 is the **admin/cashier station**. It is the only PC that can view the
cameras and manage the network gear. PC2–PC4 are customer machines.

## Security policy

| From ↓ / To → | Internet | Printers | CCTV | Management |
|---|---|---|---|---|
| Customer PCs (PC2–PC4) | ✅ via NAT | ✅ print only (TCP 9100/515/631, ping) | ❌ | ❌ |
| Admin PC (PC1) | ✅ | ✅ | ✅ | ✅ (SSH) |
| Printers | ❌ | — | ❌ | replies only |
| CCTV cameras | ❌ | ❌ | — | replies only |

How it is enforced:

- **Segmentation**: separate VLANs per device class. Inter-VLAN traffic must cross CAFE-R1.
- **ACLs on CAFE-R1** (`PCS-IN`, `PRINTERS-IN`, `CCTV-IN`) implement the matrix above.
- **NAT/PAT** only translates VLAN 10 and 99, so printers and cameras can't get online even if an ACL is misconfigured. This keeps cameras away from cloud/botnet exposure.
- **Switch hardening**: port-security (1 sticky MAC per port), BPDU guard and PortFast on edge ports, DHCP snooping (rogue DHCP blocked), unused ports shut down and parked in VLAN 999, native VLAN moved off VLAN 1, DTP disabled.
- **Device access**: SSH v2 only, local users, VTY restricted to the admin PC and the management VLAN.

Lab credentials (change for real deployments): user `admin` / `Cafe@Admin1`, enable `Cafe@Enable1`.

## Containerlab quick start

Requires Docker and [containerlab](https://containerlab.dev/install/).

```bash
cd containerlab
docker build -t cybercafe-node:1.0 image/
sudo containerlab deploy -t cybercafe.clab.yml
./verify.sh                     # runs the policy matrix as live tests
sudo containerlab destroy -t cybercafe.clab.yml
```

How the Containerlab version maps to the Cisco design:

| Packet Tracer | Containerlab node | Implementation |
|---|---|---|
| CAFE-SW1 (2960) | `sw1` | VLAN-filtering Linux bridge, eth1 trunk, VLAN 99 SVI |
| CAFE-R1 (2911) | `r1` | 802.1Q subinterfaces, `dnsmasq` DHCP, `iptables` firewall (= ACLs) and MASQUERADE (= PAT) |
| ISP + INTERNET-SRV | `isp` | WAN peer, DNS and web server on 198.51.100.10 |
| Printer-PT | `printer1`, `printer2` | RAW/JetDirect listener on TCP 9100 (jobs go to `/var/spool/print.log`) |
| Webcam (IoT) | `cam1`, `cam2` | HTTP "live view" on TCP 80 |
| PC-PT | `pc1-admin`, `pc2`–`pc4` | PC1 static, PC2–PC4 DHCP |

Useful commands:

```bash
docker exec -it clab-cybercafe-pc2 bash               # sit at a customer PC
docker exec clab-cybercafe-r1 iptables -vnL FORWARD   # ACL hit counters
docker exec clab-cybercafe-r1 cat /tmp/dnsmasq.leases # DHCP bindings
docker exec clab-cybercafe-sw1 bridge vlan show       # VLAN port map
docker exec clab-cybercafe-printer1 cat /var/spool/print.log
```

## Scaling notes

- More PCs: add access ports in VLAN 10. The /24 DHCP pool already covers 244 clients.
- Wi-Fi for guests: add an AP on a new VLAN (e.g. 40, GUEST-WIFI) with the same rules as VLAN 10.
- CCTV recording: put an NVR in VLAN 30. It needs no rule changes.
