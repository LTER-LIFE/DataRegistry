import logging
from datetime import datetime

import requests
from config import Config


def valid_token(token):
    """
    :param: token is a dictionary containing msal token
    :return: Boolean for the validity of the token

    according to M$ @ https://learn.microsoft.com/en-us/azure/active-directory/develop/id-tokens

     - Timestamps: the iat and exp timestamps should all fall before or after the current time, as appropriate.
     - Audience: the aud claim should match the app ID for your application.
    """
    try:
        if not token:
            return False
        if token.get("error"):
            logging.warning(f"login failed: {token.get('error_description')}")
            return False
        if datetime.fromtimestamp(token.get("exp")) < datetime.now():
            return False
        if datetime.fromtimestamp(token.get("iat")) > datetime.now():
            return False
        if token.get("client_id") != Config.SURF_CLIENT_ID:
            return False
    except Exception as e:
        logging.warning(f"login failed: {token} with {e}")
        return False

    return True


def get_userinfo(access_token):
    """

    :param access_token:
    :return: dictionary containing the userinfo
    """
    if not access_token:
        return None
    result = requests.post(url=Config.SURF_DOTWELLKNOWN_CONFIG['userinfo_endpoint'], data=access_token)

    if result.status_code != 200:
        return None
    return result.json()


def in_editor_group(access_token):
    """
    In editor group checks the user information 'eduperson_entitlement scope if the user is in the group that is
    selected in the config file under the name: SURF_EDITOR_GROUP, this consists of Both SURF_SRAM_GROUP_PREFIX and
    SURF_SRAM_GROUP_POSTFIX.

    :param access_token:
    :return: boolean
    """
    user_info = get_userinfo(access_token, {})
    return Config.SURF_EDITOR_GROUP in user_info.get('eduperson_entitlement', [])
