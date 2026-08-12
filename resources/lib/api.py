# -*- coding: utf-8 -*-
import json
import gzip
import uuid
from websocket import create_connection
from urllib.request import urlopen, Request
from urllib.error import HTTPError

from resources.lib.utils import appVersion,get_config_value, log_message, load_json_data, save_json_data

BASE_API_VERSION='v1.11'
APIURL = 'https://http.cms.jyxo.cz/api/'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:153.0) Gecko/20100101 Firefox/153.0'

def call_api(api, data, token = None):
    headers = {'User-Agent' : UA, 'Accept-Encoding' : 'gzip', 'Accept' : '*/*', 'Content-type' : 'application/json;charset=UTF-8'}
    api_version = load_api_version()
    url = f"{APIURL}{api_version}/{api}"
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    if get_config_value('debug') == 1 or get_config_value('debug') == '1' or get_config_value('debug') == -1 or get_config_value('debug') == '-1' or get_config_value('debug') == 'true':
        log_message(str(url))
        log_message(str(data))
    try:
        requestId = str(uuid.uuid4())
        clientId = str(uuid.uuid4())
        ws = create_connection('wss://ws.cms.jyxo.cz/websocket/' + clientId)
        ws_data = json.loads(ws.recv())
        post = {"deviceInfo":{"deviceType":"web","appVersion":appVersion,"deviceManufacturer":"Unknown","deviceOs":"Linux"},"capabilities":{"async":"websockets"},"context":{"requestId":requestId,"clientId":clientId,"sessionId":ws_data['data']['serverId'],"serverId":ws_data['data']['serverId']}}
        if data is not None:
            post = {**data, **post}
        post = json.dumps(post).encode("utf-8")
        request = Request(url = url , data = post, headers = headers)
        response = urlopen(request, timeout = 20)
        if response.getheader("Content-Encoding") == 'gzip':
            gzipFile = gzip.GzipFile(fileobj = response)
            data = gzipFile.read()
        else:
            data = response.read()
        if len(data) > 0:
            data = json.loads(data)
        if 'result' not in data or 'status' not in data['result'] or data['result']['status'] not in ['OkAsync', 'Ok']:
            log_message('Chyba při volání '+ str(url))
            ws.close()
            return {'result': {'status': 'Error', 'message': data.get('result', {}).get('message', 'Chyba při volání API')}}  
        if data['result']['status'] == 'OkAsync':
            response = ws.recv()
            if (type(get_config_value('debug')) == int and get_config_value('debug') > 0) or get_config_value('debug') == '1' or get_config_value('debug') == 'true':
                if type(get_config_value('debug')) == int and get_config_value('debug') > 1 and len(str(response)) > get_config_value('debug'):
                    log_message('Odpověď obdržena (' + str(len(str(response))) + ')')
                else:
                    log_message(str(response))        
            if response and len(response) > 0:
                data = json.loads(response)
                if 'response' not in data or 'result' not in data['response'] or 'status' not in data['response']['result'] or data['response']['result']['status'] != 'Ok' or data['response']['context']['requestId'] != requestId:
                    log_message('Chyba při volání '+ str(url))
                    log_message(str(data))
                    ws.close()
                    return { 'err' : 'Chyba při volání API' }  
                ws.close()
                if 'data' in data['response']:
                    return data['response']['data']
                return []
            else:
                ws.close()
                return []
        elif data['result']['status'] == 'Ok':
            ws.close()
            if (type(get_config_value('debug')) == int and get_config_value('debug') > 0) or get_config_value('debug') == '1' or get_config_value('debug') == 'true':
                if type(get_config_value('debug')) == int and get_config_value('debug') > 1 and len(str(data)) > get_config_value('debug'):
                    log_message('Odpověď obdržena (' + str(len(str(data))) + ')')
                else:
                    log_message(str(data))        
            if 'result' not in data or 'status' not in data['result'] or data['result']['status'] != 'Ok' or data['context']['requestId'] != requestId:
                log_message('Chyba při volání '+ str(url))
                return { 'err' : 'Chyba při volání API' }
            else:
                if 'data' in data:
                    return data['data']
            return []
    except HTTPError as e:
        log_message('Chyba při volání '+ str(url) + ': ' + e.reason)
        if str(e) == 'HTTP Error 404: Not Found':
            get_api_version()
        ws.close()
        return { 'err' : e.reason }

def get_api_version():
    import requests
    api_version = load_api_version()
    start_version = int(api_version.split('.')[1])
    for minor in range(start_version+1, 50):
        version = str(minor).zfill(2)
        url = f"{APIURL}v1.{version}/user.login.step"
        response = requests.post(url, json={})
        if response.status_code not in [400, 404]:
            return api_version
        elif response.status_code == 400:
            api_version = f"v1.{version}"
            save_api_version(api_version)
            return api_version

def load_api_version():
    data = load_json_data(file={'filename': 'api_version.txt','description': 'verze API'})
    if data:
        try:
            data = json.loads(data)
            api_version = data.get('api_version', BASE_API_VERSION)
        except (json.JSONDecodeError, ValueError):
            api_version = BASE_API_VERSION
            save_api_version(api_version)
    else:
        api_version = BASE_API_VERSION
        save_api_version(api_version)
    return api_version

def save_api_version(api_version):
    data = json.dumps({'api_version': api_version})
    save_json_data(file={'filename': 'api_version.txt','description': 'verze API'}, data=data)

