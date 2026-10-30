# Building `CyberCafe-LAN.pkt` in Cisco Packet Tracer

Tested against Packet Tracer 8.x (works the same in 7.3+). Takes about 10 minutes.

## 1. Place devices

| Qty | Packet Tracer device | Where to find it | Rename to |
|---|---|---|---|
| 1 | Router **2911** | Network Devices → Routers | `CAFE-R1` |
| 1 | Switch **2960-24TT** | Network Devices → Switches | `CAFE-SW1` |
| 4 | **PC-PT** | End Devices → End Devices | `PC1-ADMIN`, `PC2`, `PC3`, `PC4` |
| 2 | **Printer-PT** | End Devices → End Devices | `PRINTER1`, `PRINTER2` |
| 2 | **Webcam** (IoT) | End Devices → Home → Webcam | `CAM1`, `CAM2` |
| 1 | Router **2911** | Network Devices → Routers | `ISP` |
| 1 | **Server-PT** | End Devices → End Devices | `INTERNET-SRV` |

The ISP router and server stand in for the Internet so you can test NAT and
browsing. Leave them out if you only need the LAN.

> **Webcam has no Ethernet port?** Click it → **Advanced** → **I/O Config** →
> set **Network Adapter** to **PT-IOT-NM-1CFE** (FastEthernet).

## 2. Cable it

| From | Port | To | Port | Cable |
|---|---|---|---|---|
| CAFE-R1 | G0/0 | CAFE-SW1 | G0/1 | Copper straight-through |
| CAFE-R1 | G0/1 | ISP | G0/0 | Copper cross-over |
| ISP | G0/1 | INTERNET-SRV | Fa0 | Copper cross-over |
| PC1-ADMIN | Fa0 | CAFE-SW1 | Fa0/1 | Copper straight-through |
| PC2 | Fa0 | CAFE-SW1 | Fa0/2 | Copper straight-through |
| PC3 | Fa0 | CAFE-SW1 | Fa0/3 | Copper straight-through |
| PC4 | Fa0 | CAFE-SW1 | Fa0/4 | Copper straight-through |
| PRINTER1 | Fa0 | CAFE-SW1 | Fa0/5 | Copper straight-through |
| PRINTER2 | Fa0 | CAFE-SW1 | Fa0/6 | Copper straight-through |
| CAM1 | Fa0 | CAFE-SW1 | Fa0/7 | Copper straight-through |
| CAM2 | Fa0 | CAFE-SW1 | Fa0/8 | Copper straight-through |

## 3. Configure the network devices

Open each device → **CLI** tab, answer `no` to the initial setup dialog, then paste:

1. `CAFE-SW1` ← [`CAFE-SW1.txt`](CAFE-SW1.txt)
2. `CAFE-R1` ← [`CAFE-R1.txt`](CAFE-R1.txt)
3. `ISP` ← [`ISP.txt`](ISP.txt)

Paste the switch before the router so the trunk and VLANs exist when the router
subinterfaces come up.

## 4. Configure the end devices (Desktop → IP Configuration)

| Device | Mode | IP address | Mask | Gateway | DNS |
|---|---|---|---|---|---|
| PC1-ADMIN | Static | 192.168.10.10 | 255.255.255.0 | 192.168.10.1 | 198.51.100.10 |
| PC2 / PC3 / PC4 | **DHCP** | (from CAFE-R1, .11–.254) | | | |
| PRINTER1 | Static (Config → FastEthernet0) | 192.168.20.10 | 255.255.255.0 | 192.168.20.1 | |
| PRINTER2 | Static | 192.168.20.11 | 255.255.255.0 | 192.168.20.1 | |
| CAM1 | Static (Config → FastEthernet0) | 192.168.30.10 | 255.255.255.0 | 192.168.30.1 | |
| CAM2 | Static | 192.168.30.11 | 255.255.255.0 | 192.168.30.1 | |
| INTERNET-SRV | Static | 198.51.100.10 | 255.255.255.0 | 198.51.100.1 | 198.51.100.10 |

Printers and gateway: set the default gateway under **Config → Settings**.

On **INTERNET-SRV** → Services:
- **DNS**: on, add an A record `www.internet.test` → `198.51.100.10`.
- **HTTP**: on (the default page is enough).

## 5. Verify

| From | Test | Expected |
|---|---|---|
| PC2 | `ipconfig` | Address in 192.168.10.11–.254 |
| PC2 | `ping 192.168.20.10` | **Success** (customers can print) |
| PC2 | `ping 192.168.30.10` | **Fails** (customers can't see CCTV) |
| PC2 | Web Browser → `http://www.internet.test` | Page loads (NAT works) |
| PC1-ADMIN | `ping 192.168.30.10` | **Success** (admin views cameras) |
| PC1-ADMIN | `ssh -l admin 192.168.99.2` | Switch login (password `Cafe@Admin1`) |
| PRINTER1 / CAM1 | *Add Simple PDU* (envelope icon) → INTERNET-SRV | **Failed** (no Internet for printers or cameras) |
| PC3 | *Add Simple PDU* → CAM2 | **Failed** |
| CAFE-R1 | `show ip nat translations` | Entries for 192.168.10.x → 203.0.113.2 |
| CAFE-R1 | `show access-lists` | Match counters going up |
| CAFE-SW1 | `show vlan brief`, `show interfaces trunk` | Ports in VLANs 10/20/30, trunk on G0/1 |

The first ping across the router often times out once while ARP resolves. That is normal.

## 6. Save

**File → Save As → `CyberCafe-LAN.pkt`**.
