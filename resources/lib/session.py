# -*- coding: utf-8 -*-
import sys

import json
import time

from resources.lib.api import call_api
from resources.lib.utils import get_config_value, display_message, load_json_data, save_json_data, api_version

def get_token():
    post = {"payload":{"command":{"schema":"LoginWithCredentialsCommand","email":get_config_value('username'),"password":get_config_value('password')}}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.login.step', data = post)
    if 'err' in data or 'step' not in data or ('bearerToken' not in data['step'] and data['step']['schema'] != 'ShowAccountChooserStep'):        
        display_message('Problém při přihlášení')
        sys.exit()
    if data['step']['schema'] == 'ShowAccountChooserStep':
        accounts = []
        authToken = data['step']['authToken']
        for account in data['step']['accounts']:
            accounts.append(account['accountId'])

        if get_config_value('poradi_sluzby') is None:
            account_index = -1
        else:
            account_index = int(get_config_value('poradi_sluzby'))
            if account_index > len(accounts):
                account_index = -1
        idx = 1
        accountId = ''
        for account in accounts:
            if account_index > 0 and idx == account_index:
                accountId = account
            elif account_index == -1:
                accountId = account
            idx = idx + 1
        post = {"payload":{"command":{"schema":"LoginWithAccountCommand","accountId":accountId,"authCode":authToken}}}
        data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.login.step', data = post)   
        if 'err' in data or 'step' not in data or 'bearerToken' not in data['step']:
            display_message('Problém při přihlášení')
            sys.exit()            

    token = data['step']['bearerToken']
    deviceId = data['step']['currentUser']['currentDevice']['id']
    post = {"payload":{"id":deviceId,"name": get_config_value('deviceid')}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.device.change', data = post, token = token)
    post = {"payload":{"screen":"devices"}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/setting.display', data = post, token = token)
    devices = {}
    for block in data.get('screen', {}).get('blocks', []):
        if block['schema'] == 'SettingUserDevicesBlock':
            devices = block.get('devices', {}).get('devices')
    if 'err' in data:
        display_message('Problém při přihlášení')
        sys.exit()
    for device in devices:
        if device['id'] != deviceId and device['name'] ==  get_config_value('deviceid'):
            post = {"payload":{"criteria":{"schema":"UserDeviceIdCriteria","id":device['id']}}}
            data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.device.remove', data = post, token = token)

    data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.profiles.display', data = {"payload": {"mode": "change"}}, token = token)
    if 'err' in data or 'availableProfiles' not in data or 'profiles' not in data['availableProfiles']:
        display_message('Problém při přihlášení')
        sys.exit()
    for profile in data['availableProfiles']['profiles']:
        if profile['profile']['name'] == get_config_value('profile') or get_config_value('profile') is None or len(get_config_value('profile')) == 0:
            if get_config_value('profile_pin') is not None and len(get_config_value('profile_pin')) > 0 and get_config_value('profile_pin') != '4321':
                post = {"payload":{"profileId":profile['profile']['id']},"authorization":[{"schema":"PinRequestAuthorization","pin":get_config_value('profile_pin'),"type":"profile"}]}
            else:
                post = {"payload":{"profileId":profile['profile']['id']}}
            data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.profile.select', data = post, token = token)
            if 'err' in data or 'bearerToken' not in data:
                display_message('Problém při přihlášení')
                sys.exit()
            display_message('Profil: ' + profile['profile']['name'])
            token = data['bearerToken']
            return token
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
    data = json.dumps({'token' : token, 'valid_to' : int(time.time() + 60*60*4)})        
    save_json_data({'filename' : 'session.txt', 'description' : 'session'}, data)


