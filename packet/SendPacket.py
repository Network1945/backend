from typing import Optional
from scapy.all import (
    IP, TCP, UDP, ICMP, Raw,
    Ether, ARP,
    send, sr1, srp, conf
)

def send_icmp(dst_ip: str, count: int = 1, iface: Optional[str] = None, payload: Optional[bytes] = None, timeout: float = 1.0):
    pkt = IP(dst=dst_ip)/ICMP()
    if payload:
        pkt = pkt/Raw(load=payload)
    answers = []
    for _ in range(count):
        ans = sr1(pkt, timeout=timeout, iface=iface, verbose=0)
        answers.append(bool(ans))
    return {"sent": count, "replies": sum(1 for a in answers if a)}

def send_udp(dst_ip: str, dst_port: int, count: int = 1, iface: Optional[str] = None, payload: Optional[bytes] = None):
    pkt = IP(dst=dst_ip)/UDP(dport=dst_port)
    if payload:
        pkt = pkt/Raw(load=payload)
    send(pkt, count=count, iface=iface, verbose=0)
    return {"sent": count}

def send_tcp_syn(dst_ip: str, dst_port: int, count: int = 1, iface: Optional[str] = None, src_port: Optional[int] = None, flags: str = "S"):
    # 기본 SYN. flags 변경으로 "F" (FIN), "A" (ACK) 등도 가능
    layer = TCP(dport=dst_port, flags=flags)
    if src_port:
        layer.sport = src_port
    pkt = IP(dst=dst_ip)/layer
    send(pkt, count=count, iface=iface, verbose=0)
    return {"sent": count}

def send_arp(target_ip: str, iface: Optional[str] = None, timeout: float = 1.0):
    # 브로드캐스트로 대상 IP의 MAC을 질의
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp = ARP(pdst=target_ip)
    ans, _ = srp(ether/arp, timeout=timeout, iface=iface, verbose=0)
    results = []
    for snd, rcv in ans:
        results.append({"ip": rcv.psrc, "mac": rcv.hwsrc})
    return {"queries": 1, "responses": results}

# 선택에 따라 기본 인터페이스 지정 가능
def set_iface(iface: Optional[str]):
    if iface:
        conf.iface = iface