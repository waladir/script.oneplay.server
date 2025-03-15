# -*- coding: utf-8 -*-
import sys

import json
import time

from resources.lib.api import call_api
from resources.lib.utils import get_config_value, display_message, load_json_data, save_json_data

def get_token():
    post = {"payload":{"command":{"schema":"LoginWithCredentialsCommand","email":get_config_value('username'),"password":get_config_value('password')}}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/user.login.step', data = post)
    if 'err' in data or 'step' not in data or 'bearerToken' not in data['step']:
        display_message('Problém při přihlášení')
        sys.exit()
    token = data['step']['bearerToken']
    deviceId = data['step']['currentUser']['currentDevice']['id']
    post = {"payload":{"id":deviceId,"name": get_config_value('deviceid')}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/user.device.change', data = post, token = token)
    post = {"payload":{"screen":"devices"}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/setting.display', data = post, token = token)
    if 'err' in data or 'screen' not in data or 'userDevices' not in data['screen']:
        display_message('Problém při přihlášení')
        sys.exit()
    for device in data['screen']['userDevices']['devices']:
        if device['id'] != deviceId and device['name'] ==  get_config_value('deviceid'):
            post = {"payload":{"criteria":{"schema":"UserDeviceIdCriteria","id":device['id']}}}
            data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/user.device.remove', data = post, token = token)
    return token

def load_session(reset = False):
    if reset == True:
        token = get_token()
        save_session(token)
        return token
    data = load_json_data({'filename' : 'session.txt', 'description' : 'session'})
    if data is not None:
        data = json.loads(data)
        if 'valid_to' in data and 'token' in data:
            token = data['token']
            if int(data['valid_to']) < int(time.time()):
                token = get_token()
                save_session(token)
        else:
            token = get_token()
            save_session(token)
    else:
        token = get_token()
        save_session(token)
    return token

def save_session(token):
    data = json.dumps({'token' : token, 'valid_to' : int(time.time() + 60*60*24)})        
    save_json_data({'filename' : 'session.txt', 'description' : 'session'}, data)


