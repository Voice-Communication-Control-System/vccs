from django.contrib.auth.backends import BaseBackend

class VatsimOauth(BaseBackend):
    def authenticate(self, request, username=None, token=None):
        pass