# -*- coding: utf-8 -*-
import json
import time

from resources.lib.api import call_api
from resources.lib.utils import get_config_value, display_message, load_json_data, save_json_data, log_message, log_error, raise_error, OneplayError, api_version

_login_failure_until = 0
_login_failure_message = ''

def _is_debug():
    debug = get_config_value('debug')
    return debug == 1 or debug == '1' or debug == -1 or debug == '-1' or debug == 'true'

def _get_api_error(data):
    if not isinstance(data, dict):
        return None
    if 'err' in data:
        return str(data['err'])
    result = data.get('result')
    if isinstance(result, dict) and result.get('status') == 'Error':
        return result.get('message', 'Chyba při volání API')
    return None

def _collect_account_items(step):
    items = list(step.get('accounts', []))
    for group in step.get('groups', []):
        items.extend(group.get('accounts', []))
    return items

def _collect_account_ids(step):
    account_ids = []
    for acc in _collect_account_items(step):
        if acc.get('extId') or acc.get('isActive'):
            account_ids.append(acc['accountId'])
    if not account_ids:
        account_ids = [acc['accountId'] for acc in _collect_account_items(step) if acc.get('accountId')]
    return account_ids

def _fail_login(message, data=None):
    global _login_failure_until, _login_failure_message
    _login_failure_until = int(time.time()) + 300
    _login_failure_message = message
    detail = str(data) if data is not None and _is_debug() else None
    raise_error(message, detail)

def get_token():
    global _login_failure_until, _login_failure_message
    if _login_failure_until > int(time.time()):
        msg = _login_failure_message + ' (další pokus za ' + str(_login_failure_until - int(time.time())) + ' s)'
        log_error(msg)
        raise OneplayError(msg)

    post = {"payload":{"command":{"schema":"LoginWithCredentialsCommand","email":get_config_value('username'),"password":get_config_value('password')}}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.login.step', data = post)
    api_error = _get_api_error(data)
    if api_error or 'step' not in data or ('bearerToken' not in data['step'] and data['step']['schema'] != 'ShowAccountChooserStep'):
        message = 'Problém při přihlášení'
        if api_error:
            message = message + ': ' + api_error
        _fail_login(message, data)

    if data['step']['schema'] == 'ShowAccountChooserStep':
        accounts = _collect_account_ids(data['step'])
        authToken = data['step']['authToken']
        if not accounts:
            if _is_debug():
                log_message('ShowAccountChooserStep keys: ' + str(list(data['step'].keys())))
                log_message('ShowAccountChooserStep: ' + str(data['step']))
            _fail_login('Problém při přihlášení - žádné dostupné účty', data)

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
        if _is_debug():
            log_message('Dostupné účty: ' + str(len(accounts)) + ', vybraný (poradi_sluzby=' + str(account_index) + '): ' + str(accountId))
        post = {"payload":{"command":{"schema":"LoginWithAccountCommand","accountId":accountId,"authCode":authToken}}}
        data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.login.step', data = post)
        api_error = _get_api_error(data)
        if api_error or 'step' not in data or 'bearerToken' not in data['step']:
            message = 'Problém při přihlášení'
            if api_error:
                message = message + ': ' + api_error
            _fail_login(message, data)

    _login_failure_until = 0
    _login_failure_message = ''
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
        _fail_login('Problém při přihlášení', data)
    for device in devices:
        if device['id'] != deviceId and device['name'] ==  get_config_value('deviceid'):
            post = {"payload":{"criteria":{"schema":"UserDeviceIdCriteria","id":device['id']}}}
            data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.device.remove', data = post, token = token)

    data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.profiles.display', data = {"payload": {"mode": "change"}}, token = token)
    if 'err' in data or 'availableProfiles' not in data or 'profiles' not in data['availableProfiles']:
        _fail_login('Problém při přihlášení', data)
    for profile in data['availableProfiles']['profiles']:
        if profile['profile']['name'] == get_config_value('profile') or get_config_value('profile') is None or len(get_config_value('profile')) == 0:
            if get_config_value('profile_pin') is not None and len(get_config_value('profile_pin')) > 0 and get_config_value('profile_pin') != '4321':
                post = {"payload":{"profileId":profile['profile']['id']},"authorization":[{"schema":"PinRequestAuthorization","pin":get_config_value('profile_pin'),"type":"profile"}]}
            else:
                post = {"payload":{"profileId":profile['profile']['id']}}
            data = call_api(url = 'https://http.cms.jyxo.cz/api/' + api_version + '/user.profile.select', data = post, token = token)
            if 'err' in data or 'bearerToken' not in data:
                _fail_login('Problém při přihlášení', data)
            display_message('Profil: ' + profile['profile']['name'])
            token = data['bearerToken']
            return token
    return token

def load_session(reset = False):
    global _login_failure_until, _login_failure_message
    if reset == True:
        _login_failure_until = 0
        _login_failure_message = ''
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


