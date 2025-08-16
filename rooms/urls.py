from django.urls import path
from .views import SignupView, LoginView, RoomCreateView, RoomDetailView, RoomListView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/",  LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("create/", RoomCreateView.as_view()),             # POST /rooms/
    path("list/", RoomListView.as_view(), name="room-list"),  # /rooms/list/
    path("<slug:id>/", RoomDetailView.as_view()),   # GET  /rooms/<roomId>/

]