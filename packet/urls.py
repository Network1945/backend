from django.contrib import admin
from django.urls import path
from .views import SendPacketAPI

urlpatterns = [
    path('api/send-packet/', SendPacketAPI.as_view()),
]