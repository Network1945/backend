from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import SignupSerializer, LoginSerializer

User = get_user_model()

def _tokens_for_user(user: User):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": {"id": user.id, "name": user.name},
    }

class SignupView(generics.CreateAPIView):
    """
    회원가입: 계정만 만들고 토큰은 발급하지 않음.
    """
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        # resp.data: {"id": ..., "name": ...}  (serializer가 password는 write_only)
        return Response({"ok": True, "user": resp.data}, status=201)


class LoginView(generics.GenericAPIView):
    """
    로그인: 자격 검증 후 JWT(access/refresh) 발급.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.validated_data["user"]
        return Response(_tokens_for_user(user), status=200)



# rooms/views_room.py
from rest_framework import generics, permissions
from .models import Room
from .serializers import RoomCreateSerializer, RoomDetailSerializer

class RoomCreateView(generics.CreateAPIView):
    """
    POST /rooms/   (JWT 필요)
    응답: {"roomId": "<id>"}
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = Room.objects.all()
    serializer_class = RoomCreateSerializer

class RoomDetailView(generics.RetrieveAPIView):
    """
    GET /rooms/<roomId>/   (JWT 필요)
    응답: {"roomId","host","status","created_at"}
    """
    permission_classes = [permissions.AllowAny]
    queryset = Room.objects.all()
    lookup_field = "id"
    serializer_class = RoomDetailSerializer


class RoomListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]         # 목록은 누구나 가능
    queryset = Room.objects.all().order_by("-created_at")
    serializer_class = RoomDetailSerializer