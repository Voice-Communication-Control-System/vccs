import json
import re
import requests

from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from loguru import logger

VATSIM_OAUTH_BASE_URL = "https://auth.vatsim.net"
VATSIM_OAUTH_AUTHORISE = "/oauth/authorize"
VATSIM_OAUTH_TOKEN = "/oauth/token"
VATSIM_OAUTH_API = "/api/user"
VATSIM_OAUTH_CLIENT_ID = "1063"
VATSIM_OAUTH_CLIENT_SECRET = "chXH8MjEsxeJinERzuMGLy2S0zbxhdRseMeCFjfW"
VATSIM_OAUTH_REDIRECT_URL = "https://vccs.vnpas.uk/oauth/token/"

def authenticate(request):
    """
    Redirect the user to VATSIM SSO if no token found
    """
    try:
        access_token = request.session.get("access_token")
        logger.debug("Using stored access token")
        return get_user(access_token, request)
    except KeyError:
        logger.debug("No stored access token so requesting from VATSIM")
        login_redirect = f"{VATSIM_OAUTH_BASE_URL}{VATSIM_OAUTH_AUTHORISE}?client_id={VATSIM_OAUTH_CLIENT_ID}&redirect_uri={VATSIM_OAUTH_REDIRECT_URL}&response_type=code&scope=full_name+vatsim_details+email+country"
        return redirect(login_redirect)

def token(request):
    """
    What to do with the returned token
    """
    # get the token from the url
    code = request.GET.get("code")
    logger.debug("Authorisation code received from VATSIM")
    logger.trace(code)

    # generate the POST request
    rqst_access_token = {
        "grant_type": "authorization_code",
        "client_id": VATSIM_OAUTH_CLIENT_ID,
        "client_secret": VATSIM_OAUTH_CLIENT_SECRET,
        "redirect_uri": VATSIM_OAUTH_REDIRECT_URL,
        "code": code
    }
    rqst_post = requests.post(f"{VATSIM_OAUTH_BASE_URL}{VATSIM_OAUTH_TOKEN}", json=rqst_access_token)
    json_response = json.loads(rqst_post.text)
    logger.debug("Authorisation response received from VATSIM")
    logger.trace(json_response)

    # get the access token to permit obtaining user details
    try:
        # load the access token
        token = json_response["access_token"]
        # pass to VATSIM to get user details
        response = get_user(token, request)
        logger.debug(response)
        # securely write the access token to a cookie
        request.session["access_token"] = token
        return redirect("/")
    except KeyError:
        try:
            del request.session["access_token"]
        except KeyError:
            pass        
        return HttpResponseForbidden("Invalid access token provided. Please use the 'back' button on your browser to try again.")


def get_user(auth_token, rqst):
    """
    Passes an auth token to VATSIM to get user details.
    """
    rqst_headers = {
        "Authorization": f"Bearer {auth_token}",
        "Accept": "application/json"
    }
    user_details = requests.get(f"{VATSIM_OAUTH_BASE_URL}{VATSIM_OAUTH_API}", headers=rqst_headers)
    json_response = json.loads(user_details.text)

    # quick test to see if user has been returned
    cid = json_response["data"]["cid"]
    if re.match(r'[\d]{6,8}', cid):
        rqst.session["cid"] = json_response["data"]["cid"]
        rqst.session["data"] = json_response["data"]
        return json_response["data"]
    return False
