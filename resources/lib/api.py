# -*- coding: utf-8 -*-
# SHARED: Oneplay, Oneplay Server, TVheadend
import gzip
import json
import re
import socket
import sys
import uuid

from urllib.error import HTTPError
from urllib.request import Request, urlopen

from websocket import create_connection

from resources.lib.utils import (
    Settings,
    display_dialog_pin,
    display_dialog_yn,
    display_message,
    get_config_value,
    is_kodi,
    log_message,
)


class API:
    def __init__(self):
        self.APIURL = 'https://http.cms.jyxo.cz/api/'
        self.UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0'
        self.HEADERS = {
            'User-Agent': self.UA,
            'Accept-Encoding': 'gzip',
            'Accept': '*/*',
            'Content-type': 'application/json;charset=UTF-8',
        }
        self.APPVERSION = 'R11.33'
        self.BASE_API_VERSION = 'v1.11'
        self.API_VERSION_FILE = {'filename': 'api_version.txt', 'description': 'verze API'}

    def get_version(self):
        import requests

        self.load_api_version()
        try:
            start_version = int(self.api_version.split('.')[1])
        except (IndexError, ValueError):
            start_version = int(self.BASE_API_VERSION.split('.')[1])
        for minor in range(start_version + 1, 50):
            version = str(minor).zfill(2)
            url = f"{self.APIURL}v1.{version}/user.login.step"
            try:
                response = requests.post(url, json={}, timeout=20)
            except requests.RequestException as error:
                log_message(f"Oneplay > Chyba při ověřování verze API: {error}")
                return
            if response.status_code not in (400, 404):
                return
            if response.status_code == 400:
                self.api_version = f"v1.{version}"
                self.save_api_version()
                return

    def load_api_version(self):
        """Načte verzi API"""
        self.api_version = self.BASE_API_VERSION
        settings = Settings()
        data = settings.load_json_data(file_info=self.API_VERSION_FILE)
        if data:
            try:
                data = json.loads(data) or {}
                self.api_version = data.get('api_version', self.BASE_API_VERSION)
            except (AttributeError, json.JSONDecodeError, ValueError):
                self.save_api_version()
        else:
            self.save_api_version()

    def save_api_version(self):
        """Uloží verzi API"""
        settings = Settings()
        data = json.dumps({'api_version': self.api_version})
        settings.save_json_data(file_info=self.API_VERSION_FILE, data=data)

    def call_api(self, api, data, session=None, sensitive=False):
        """Volání API Oneplay včetně ošetření logování"""
        self.load_api_version()
        url = f"{self.APIURL}{self.api_version}/{api}"
        if session and session.token:
            self.HEADERS['Authorization'] = f"Bearer {session.token}"
        else:
            self.HEADERS.pop('Authorization', None)

        debug = get_config_value('debug') in (1, '1', -1, '-1', 'true')
        if get_config_value('log_request_url') == 'true' or debug:
            log_message(f"Oneplay > {url}")
        if (get_config_value('log_request_data') == 'true' or debug) and data is not None and not sensitive:
            log_message(f"Oneplay > {data}")

        ws = None
        try:
            request_id = str(uuid.uuid4())
            client_id = str(uuid.uuid4())
            ws = create_connection(f"wss://ws.cms.jyxo.cz/websocket/{client_id}", timeout=10)
            ws_init = json.loads(ws.recv())
            server_id = ws_init['data']['serverId']
            post = {
                "deviceInfo": {
                    "deviceType": "web",
                    "appVersion": self.APPVERSION,
                    "deviceManufacturer": "Unknown",
                    "deviceOs": "Linux",
                },
                "capabilities": {"async": "websockets"},
                "context": {
                    "requestId": request_id,
                    "clientId": client_id,
                    "sessionId": server_id,
                    "serverId": server_id,
                },
            }
            if data:
                post.update(data)
            post = json.dumps(post).encode("utf-8")
            request = Request(url=url, data=post, headers=self.HEADERS)
            with urlopen(request, timeout=20) as response:
                data = response.read()
                if response.getheader("Content-Encoding") == 'gzip':
                    data = gzip.decompress(data)
            data = json.loads(data) if data else {}
            status = data.get('result', {}).get('status')
            if status not in ('OkAsync', 'Ok'):
                log_message(f"Oneplay > Chyba při volání {url}")
                message = data.get('result', {}).get('message', 'Chyba při volání API')
                return {'result': {'status': 'Error', 'message': message}}

            final_data = {}
            if status == 'OkAsync':  # asynchronní odpověď z websocketu
                ws_resp = ws.recv()
                if ws_resp:
                    ws_data = json.loads(ws_resp)
                    if ws_data.get('response', {}).get('context', {}).get('requestId') != request_id:
                        ws_resp = ws.recv()
                        ws_data = json.loads(ws_resp)
                    final_data = ws_data.get('response') or {}
            else:  # synchronní volání
                final_data = data

            if get_config_value('log_response') == 'true' or debug:
                response_text = str(final_data)
                skip_long = get_config_value('skip_long')
                if len(response_text) > 5000 and (skip_long == 'true' or not skip_long):
                    log_message(f"Oneplay > odpověď obdržena ({len(response_text)})")
                else:
                    log_message(f"Oneplay > {final_data}")

            if (final_data.get('result', {}).get('status') != 'Ok'
                    or final_data.get('context', {}).get('requestId') != request_id):
                log_message(f"Oneplay > Chyba při volání {url}")
                message = final_data.get('result', {}).get('message', 'Chyba při volání API')
                return {'result': {'status': 'Error', 'message': message}}
            return {'result': {'status': 'Ok', 'data': final_data.get('data', {})}}
        except (HTTPError, socket.timeout, socket.error) as error:
            log_message(f"Oneplay > Network Error: {error}")
            if getattr(error, 'code', None) == 404:
                self.get_version()
            return {'result': {'status': 'Error', 'message': 'Síťová chyba nebo timeout'}}
        except Exception as error:
            log_message(f"Oneplay > Neočekávaná chyba: {error}")
            return {'result': {'status': 'Error', 'message': 'Interní chyba doplňku'}}
        finally:
            if ws:
                try:
                    ws.close()
                except Exception as error:
                    log_message(f"Oneplay > Chyba při zavírání websocketu: {error}")
    
    def error_handling(self, message):
        """Ošetření chyb z volání API"""
        display_message(message)
        sys.exit()

    def _check_response(self, response, error_msg, fatal=True):
        """Kontrola chyb"""
        response = response or {}
        if response.get('result', {}).get('status') != 'Ok':
            error_detail = response.get('result', {}).get('message', 'Neznámá chyba')
            if fatal:
                display_message(error_msg)
                self.error_handling(error_detail)
        return response.get('result', {}).get('data')

    def user_login_step(self, username, password):
        """Přihlášení s výběrem účtu podle prostředí, ve kterém API běží."""
        post = {
            "payload": {
                "command": {
                    "schema": "LoginWithCredentialsCommand",
                    "email": username,
                    "password": password,
                }
            }
        }
        response = self.call_api('user.login.step', data=post, sensitive=True)
        if response.get('result', {}).get('status') != 'Ok':
            response = self.call_api('user.login.step', data=post, sensitive=True)
        data = self._check_response(response, 'Problém při přihlášení')
        step = data.get('step', {})
        if step.get('schema') != 'ShowAccountChooserStep':
            return data

        is_video_addon = False
        if is_kodi():
            try:
                import xbmcaddon

                is_video_addon = xbmcaddon.Addon().getAddonInfo('id') == 'plugin.video.oneplay'
            except Exception:
                pass

        if is_video_addon:
            from resources.lib.profiles import get_account_id

            accounts_map = {}
            accounts_list = []
            for group in step.get('groups') or []:
                for account in group.get('accounts') or []:
                    if account.get('extId') or account.get('isActive'):
                        suffix = account.get('extId') or account.get('accountProvider', 'Unknown')
                        display_name = f"{account['name']}|{suffix}"
                        accounts_map[display_name] = account.get('accountId')
                        accounts_list.append(display_name)
            selected_name = get_account_id(accounts_list)
            account_id = accounts_map.get(selected_name)
            if not account_id and selected_name:
                account_id = next(
                    (item_id for name, item_id in accounts_map.items() if name.startswith(selected_name)),
                    None,
                )
        else:
            accounts = [
                account
                for group in (step.get('groups') or [])
                for account in (group.get('accounts') or [])
                if account.get('accountId')
            ]
            account = next((item for item in accounts if item.get('isActive')), None)
            account = account or (accounts[0] if accounts else {})
            account_id = account.get('accountId')

        if not account_id:
            self.error_handling('Nebyl nalezen žádný dostupný účet')
        post_account = {
            "payload": {
                "command": {
                    "schema": "LoginWithAccountCommand",
                    "accountId": account_id,
                    "authCode": step.get('authToken'),
                }
            }
        }
        response = self.call_api('user.login.step', data=post_account)
        return self._check_response(response, 'Problém při výběru účtu')
    def user_device_change(self, id, name, session):
        """Přejmenování zařízení"""
        post = {"payload": {"id": id, "name": name}}
        return self.call_api('user.device.change', data=post, session=session)

    def user_device_remove(self, id, session):
        """Odstranění zařízení"""
        post = {"payload": {"criteria": {"schema": "UserDeviceIdCriteria", "id": id}}}
        return self.call_api('user.device.remove', data=post, session=session)

    def setting_display(self, screen, session):
        """Načtení nastavení z Oneplay"""
        post = {"payload": {"screen": screen}}
        return self._check_response(self.call_api('setting.display', data=post, session=session), 'Problém při načtení nastavení')

    def user_profiles_display(self, session):
        """Načtení profilů"""
        response = self.call_api(
            'user.profiles.display',
            data={"payload": {"mode": "change"}},
            session=session,
        )
        return self._check_response(response, 'Chyba při načtení profilů')
        
    def user_profile_select(self, profileId, profile_pin, session, is_retry=False):
        """Výběr profilu"""
        if not profileId:
            return None        
        post = {"payload": {"profileId": profileId}}
        if profile_pin and profile_pin != '4321':
            post["authorization"] = [{"schema": "PinRequestAuthorization", "pin": str(profile_pin), "type": "profile"}]
        response = self.call_api('user.profile.select', data=post, session=session)
        result = response.get('result', {})
        if result.get('status') == 'Ok':
            return result.get('data')
        if result.get('message') == 'Profil nenalezen' and not is_retry:
            from resources.lib.profiles import get_profile_id
            new_profile_id = get_profile_id(session, reset=True)
            return self.user_profile_select(new_profile_id, profile_pin, session, is_retry=True)
        error_detail = result.get('message', 'Neznámá chyba')
        display_message('Chyba při výběru profilu')
        self.error_handling(error_detail)

    def epg_channels_display(self, profileId, session):
        """Načtení seznamu kanálů pro daný profil"""
        post = {"payload": {"profileId": str(profileId)}}
        return self._check_response(self.call_api('epg.channels.display', data=post, session=session), 'Problém při načtení kanálů')
       
    def content_play(self, post, session, is_retry=False, is_next=False):
        """Získání URL streamu včetně ošetření některých chybových stavů"""
        api = 'content.playnext' if is_next else 'content.play'
        response = self.call_api(api, data=post, session=session)
        result = response.get('result', {})
        if result.get('status') == 'Ok':
            return result.get('data')
        message = result.get('message', '')
        if message == 'Kdo se dívá?' and not is_retry:
            session.reload_profile()
            return self.content_play(post, session, is_retry=True, is_next=is_next)
        if message == 'Potvrďte spuštění dalšího videa':
            if display_dialog_yn('Potvrzení spuštění', 'Máte limitovaný počet přehrání. Opravdu chcete pořad přehrát?'):
                post['authorization'] = [{"schema": "UserConfirmAuthorization", "type": "tasting"}]
                return self.content_play(post, session, is_retry=is_retry, is_next=is_next)
        elif message == 'Zadejte kód rodičovského zámku':
            pin = get_config_value('pin')
            if pin in ('1621', '4321', ''): # pokud neni PIN nastaveny, nebo ma vychozi hodnotu, zobrazi se dotaz 
                pin = display_dialog_pin()
                if len(str(pin)) != 4:
                    display_message('Nesprávný PIN')
                    pin = '1621'
            post['authorization'] = [{"schema": "PinRequestAuthorization", "pin": str(pin), "type": "parental"}]
            return self.content_play(post, session, is_next=is_next)
        if not is_next:
            display_message('Chyba při přehrání')
            display_message(message)
        return None

    def page_content_display(self, post, session):
        """Stažení detailů o pořadu (payload i metadata)"""
        seasons = []
        episodes = []
        response = self.call_api('page.content.display', post, session)
        if response.get('result', {}).get('message', '') == 'Zadejte kód rodičovského zámku':
            pin = get_config_value('pin')
            if pin in ('1621', '4321', ''): # pokud neni PIN nastaveny, nebo ma vychozi hodnotu, zobrazi se dotaz 
                pin = display_dialog_pin()
                if len(str(pin)) != 4:
                    display_message('Nesprávný PIN')
                    pin = '1621'
            post['authorization'] = [{"schema": "PinRequestAuthorization", "pin": str(pin), "type": "parental"}]
            return self.page_content_display(post, session)
        else:
            data = self._check_response(response, "Chyba načtení dat o pořadu", fatal=False) or {}
        payload = None
        meta = data.get('metadata') or {}
        layout = data.get('layout') or {}
        for block in layout.get('blocks') or []:
            schema = block.get('schema')
            if not payload and schema == 'ContentHeaderBlock':
                main_action = block.get('mainAction') or {}
                action = main_action.get('action') or {}
                if action.get('call') == 'content.play':
                    payload = (action.get('params') or {}).get('payload')
            if not meta: # pokud se blok neobsahuje přimo metadata (např. TV pořady), pokusí se je načíst z bloku
                meta = block
        # nacitani sezon a epizod                    
        # skontroluje se, ze je aktivni zalozka cele dily a pokud ne, aktivuje se
        for block in layout.get('blocks') or []:
            if block.get('schema') == 'TabBlock' and block.get('template') == 'tabs':
                for tab in block.get('tabs') or []:
                    if (tab.get('label') or {}).get('name') == 'Celé díly':
                        if tab.get('isActive'):
                            data = block
                        else:
                            post = {"payload": {"tabId": tab.get('id')}}
                            response = self.call_api('tab.display', post, session)
                            data = self._check_response(response, "Chyba načtení dat o pořadu") or {}
        # prochazi blok se seznamem dilu a sezon
        layout = data.get('layout') or {}
        for block in layout.get('blocks') or []:
            carousels = block.get('carousels') or []
            if not carousels:
                continue
            carousel = carousels[0]
            episodes.extend(carousel.get('tiles') or [])
            criteria = (carousel.get('criteria') or [{}])[0]
            if criteria.get('template') == 'showSeason':
                for item in criteria.get('items') or []:
                    if item.get('label') and item.get('criteria'):
                        seasons.append({
                            'label': item['label'],
                            'carouselId': carousel.get('id'),
                            'criteria': item['criteria'],
                        })
        seasons.sort(
            key=lambda item: int((re.findall(r'\d+', item['label']) or [0])[0]),
            reverse=True,
        )
        info = {
            'title': meta.get('title', ''),
            'plot': meta.get('description') or meta.get('plot', ''),
            'original_title': meta.get('originalTitle', ''),
            'year': str(meta.get('year', '')),
            'duration': meta.get('duration', 0),
            'genre': meta.get('genres', []) or [],
            'director': meta.get('directors', []) or [],
            'cast': meta.get('actors', []) or meta.get('cast', []) or [],
            'country': meta.get('countries', []) or meta.get('country', ''),
        }
        return {'payload': payload, 'info': info, 'seasons': seasons, 'episodes': episodes}

    def page_category_display(self, post, session):
        """Načtení kategorie"""
        response = self.call_api('page.category.display', data=post, session=session)
        data = self._check_response(response, 'Problém při načtení kategorie') or {}
        return (data.get('layout') or {}).get('blocks') or []

    def carousel_display(self, post, session, silent=False):
        """Načtení kategorie"""
        response = self.call_api('carousel.display', data=post, session=session)
        if silent and response.get('result', {}).get('status') != 'Ok':
            return {}
        data = self._check_response(response, 'Problém při načtení kategorie') or {}
        return data.get('carousel') or []

    def app_init(self, session):
        """Načtení menu kategorií"""
        post = {"payload": {"reason": "start"}}
        return self._check_response(self.call_api('app.init', data=post, session=session), 'Problém při načtení kategorií')

    def user_list_change(self, id, operation, session):
        """Přidání nebo odebrání položky uživatelského seznamu."""
        post = {"payload": {"changes": [{"schema": "UserMyListChange", "ref": {"schema": "MyListRef", "id": id}, "type": operation}]}}
        response = self.call_api('user.list.change', data=post, session=session)
        return response.get('result', {}).get('status') == 'Ok'
    
    def page_search_display(self, query, session):
        """Vyhledávání"""
        post = {"payload": {"query": query}}
        return self._check_response(self.call_api('page.search.display', data=post, session=session), 'Problém při vyhledávání')
