from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.vccs_main_panel, name='vccs-panel'),
    re_path(r'^(?P<aerodrome_icao>[A-Za-z]{3,4})/$', views.vccs_main_panel, name='vccs-panel'),
]