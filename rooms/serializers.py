# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import get_user_model

User = get_user_model()

class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        # 비밀번호 해싱
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)


class LoginSerializer(serializers.Serializer):
    name = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        name = attrs.get("name")
        password = attrs.get("password")

        try:
            user = User.objects.get(name=name)
        except User.DoesNotExist:
            raise serializers.ValidationError("No such user")

        if not check_password(password, user.password):
            raise serializers.ValidationError("Wrong password")

        attrs["user"] = user
        return attrs