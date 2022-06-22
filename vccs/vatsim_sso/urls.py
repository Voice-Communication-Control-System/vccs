from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.authenticate, name='auth-user'),
    path('token/', views.token, name='token'),
]