# views.py (SendPacketAPI만 발췌)
import socket
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, authentication

from .Serializer import SendPacketSerializer
from .SendPacket import (
    send_icmp, send_udp, send_tcp_syn, send_arp, set_iface
)

def _resolve_server_ip() -> str:
    """
    백엔드 서버 IP 강제 결정:
    1) settings.SERVER_IP가 있으면 우선 사용
    2) 없으면 hostname 기반 IP (안 되면 127.0.0.1)
    """
    ip = getattr(settings, "SERVER_IP", None)
    if ip:
        return ip
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"

class SendPacketAPI(APIView):
    permission_classes = [permissions.AllowAny]  # 외부에서 막을 거면 여기 바꿔도 됨

    def post(self, request):
        serializer = SendPacketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        params = serializer.validated_data
        iface = params.get("iface")
        set_iface(iface)

        # ✅ 무조건 백엔드 서버 IP로 강제
        target_ip = "127.0.0.1"

        try:
            ptype = params["type"]
            if ptype == "ICMP":
                result = send_icmp(
                    dst_ip=target_ip,
                    count=params.get("count", 1),
                    iface=iface,
                    payload=(params.get("payload") or "").encode() if params.get("payload") else None,
                    timeout=params.get("timeout", 1.0),
                )
            elif ptype == "UDP":
                result = send_udp(
                    dst_ip=target_ip,
                    dst_port=params["target_port"],
                    count=params.get("count", 1),
                    iface=iface,
                    payload=(params.get("payload") or "").encode() if params.get("payload") else None,
                )
            elif ptype == "TCP":
                result = send_tcp_syn(
                    dst_ip=target_ip,
                    dst_port=params["target_port"],
                    count=params.get("count", 1),
                    iface=iface,
                    src_port=params.get("src_port"),
                    flags=params.get("tcp_flags","S") or "S"
                )
            elif ptype == "ARP":
                result = send_arp(
                    target_ip=target_ip,
                    iface=iface,
                    timeout=params.get("timeout", 1.0)
                )
            else:
                return Response({"error": "unsupported type"}, status=400)

            return Response({"ok": True, "type": ptype, "result": result}, status=200)

        except PermissionError as e:
            return Response({"error": str(e)}, status=401)
        except Exception as e:
            return Response({"ok": False, "error": repr(e)}, status=500)