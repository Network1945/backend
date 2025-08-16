from django.urls import path, include
from .views import game_view

urlpatterns = [
    path("", game_view),
]