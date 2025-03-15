# -*- coding: utf-8 -*-
import json
import gzip
import uuid
from websocket import create_connection
from urllib.request import urlopen, Request
from urllib.error import HTTPError

from resources.lib.utils import appVersion,get_config_value, log_message

def call_api(url, data, token = None):
    headers = {'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0', 'Accept-Encoding' : 'gzip', 'Accept' : '*/*', 'Content-type' : 'application/json;charset=UTF-8'} 
    if token is not None:
        headers['Authorization'] = 'Bearer ' + token
    if get_config_value('debug') == 1 or get_config_value('debug') == 'true':
        log_message(str(url))
    if get_config_value('debug') == 1 or get_config_value('debug') == 'true':
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
        if 'result' not in data or 'status' not in data['result'] or data['result']['status'] != 'OkAsync':
            log_message('Chyba při volání '+ str(url))
            ws.close()
            return { 'err' : 'Chyba při volání API' }  
        response = ws.recv()
        if get_config_value('debug') == 1 or get_config_value('debug') == 'true':
            log_message(str(response))        
        if response and len(response) > 0:
            data = json.loads(response)
            if 'response' not in data or 'result' not in data['response'] or 'status' not in data['response']['result'] or data['response']['result']['status'] != 'Ok' or data['response']['context']['requestId'] != requestId:
                log_message('Chyba při volání '+ str(url))
                ws.close()
                return { 'err' : 'Chyba při volání API' }  
            ws.close()
            if 'data' in data['response']:
                return data['response']['data']
            return []
        else:
            ws.close()
            return []
    except HTTPError as e:
        log_message('Chyba při volání '+ str(url) + ': ' + e.reason)
        ws.close()
        return { 'err' : e.reason }  
