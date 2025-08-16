from rest_framework import serializers

class SendPacketSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["ICMP", "UDP", "TCP", "ARP"])
    target_ip = serializers.IPAddressField(required=False, default="127.0.0.1"), # ICMP/UDP/TCP/ARP에서 사용
    target_port = serializers.IntegerField(required=False, min_value=1, max_value=65535, default=4321)  # UDP/TCP
    count = serializers.IntegerField(required=False, min_value=1, default=1)
    iface = serializers.CharField(required=False, allow_blank=True)
    payload = serializers.CharField(required=False, allow_blank=True)  # 임의 페이로드
    tcp_flags = serializers.CharField(required=False, allow_blank=True) # "S","A","F" 등
    src_port = serializers.IntegerField(required=False, min_value=1, max_value=65535)

    timeout = serializers.FloatField(required=False, min_value=0.1, default=1.0)

    def validate(self, data):
        t = data["type"]
        # if t in ("ICMP", "ARP"):
        #     if "target_ip" not in data:
        #         raise serializers.ValidationError("target_ip is required for ICMP/ARP")
        # ifc          raise serializers.ValidationError(f"{f} is required for {t}")
        return data