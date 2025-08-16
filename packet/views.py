from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, authentication

from .Serializer import SendPacketSerializer
from .SendPacket import (
    send_icmp, send_udp, send_tcp_syn, send_arp, set_iface
)

class SendPacketAPI(APIView):
    permission_classes = [permissions.AllowAny]  # auth에서 막으니 여기선 AllowAny

    def post(self, request):
        serializer = SendPacketSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        params = serializer.validated_data
        iface = params.get("iface")
        set_iface(iface)

        try:
            ptype = params["type"]
            if ptype == "ICMP":
                result = send_icmp(
                    dst_ip=params["target_ip"],
                    count=params.get("count", 1),
                    iface=iface,
                    payload=(params.get("payload") or "").encode() if params.get("payload") else None,
                    timeout=params.get("timeout", 1.0),
                )
            elif ptype == "UDP":
                result = send_udp(
                    dst_ip=params["target_ip"],
                    dst_port=params["target_port"],
                    count=params.get("count", 1),
                    iface=iface,
                    payload=(params.get("payload") or "").encode() if params.get("payload") else None,
                )
            elif ptype == "TCP":
                result = send_tcp_syn(
                    dst_ip=params["target_ip"],
                    dst_port=params["target_port"],
                    count=params.get("count", 1),
                    iface=iface,
                    src_port=params.get("src_port"),
                    flags=params.get("tcp_flags","S") or "S"
                )
            elif ptype == "ARP":
                result = send_arp(
                    target_ip=params["target_ip"],
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