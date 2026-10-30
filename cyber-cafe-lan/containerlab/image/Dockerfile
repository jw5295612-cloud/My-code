# One small image for every lab node (router, switch, PCs, printers, cameras, ISP).
# Build once:  docker build -t cybercafe-node:1.0 image/
FROM alpine:3.20
RUN apk add --no-cache \
      bash iproute2 iptables ethtool dnsmasq socat curl \
      tcpdump bind-tools iputils netcat-openbsd
CMD ["tail", "-f", "/dev/null"]
