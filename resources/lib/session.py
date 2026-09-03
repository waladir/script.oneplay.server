# -*- coding: utf-8 -*-
# SHARED: Oneplay, Oneplay Server, TVheadend
import json
import time

from resources.lib.api import API
from resources.lib.profiles import get_profile_id
from resources.lib.utils import Settings, get_config_value, display_message


class Session:
    TOKEN_VALIDITY = 4 * 60 * 60  # 4 hodiny
    SESSION_FILE = {'filename': 'session.txt', 'description': 'session'}

    def __init__(self):
        self.token = None
        self.load_session()

    def create_session(self):
        """Proces přihlášení"""
        api = API()
        data = api.user_login_step(
            username=get_config_value('username'),
            password=get_config_value('password'),
        ) or {}
        step = data.get('step') or {}
        self.token = step.get('bearerToken')
        current_user = step.get('currentUser') or {}
        current_device = current_user.get('currentDevice') or {}
        device_id = current_device.get('id')
        if device_id:
            self.manage_devices(deviceId=device_id)
        self.reload_profile()

    def manage_devices(self, deviceId):
        """Přejmenuje aktuální zařízení a odstraní ostatní stejným jménem"""
        device_name = get_config_value('deviceid')
        if not device_name:
            return

        api = API()
        api.user_device_change(id=deviceId, name=device_name, session=self)
        data = api.setting_display(screen='devices', session=self) or {}
        devices = []
        screen = data.get('screen') or {}
        for block in screen.get('blocks') or []:
            if block.get('schema') == 'SettingUserDevicesBlock':
                devices = block.get('devices', {}).get('devices') or []
                break

        for device in devices:
            if device.get('id') != deviceId and device.get('name') == device_name:
                api.user_device_remove(id=device.get('id'), session=self)

    def reload_profile(self):
        """Znovu vybere profil"""
        api = API()
        data = api.user_profile_select(
            profileId=get_profile_id(session=self),
            profile_pin=get_config_value('profile_pin'),
            session=self,
        ) or {}
        token = data.get('bearerToken')
        if token:
            self.token = token
            self.save_session()

    def load_session(self):
        """Načte session, kontroluje integritu a expiraci"""
        settings = Settings()
        data = settings.load_json_data(file_info=self.SESSION_FILE)
        if data:
            try:
                data = json.loads(data) or {}
                token = data.get('token')
                valid_to = data.get('valid_to', 0)
                if token and int(valid_to) > int(time.time()):
                    self.token = token
                    return
            except (AttributeError, TypeError, json.JSONDecodeError, ValueError):
                pass
        self.create_session()

    def save_session(self):
        """Uloží aktuální token"""
        settings = Settings()
        valid_to = int(time.time() + self.TOKEN_VALIDITY)
        data = json.dumps({'token': self.token, 'valid_to': valid_to})
        settings.save_json_data(file_info=self.SESSION_FILE, data=data)

    def remove_session(self):
        """Smaže session a vytvoří novou session"""
        settings = Settings()
        settings.reset_json_data(file_info=self.SESSION_FILE)
        self.create_session()
        display_message('Byla vytvořena nová session')
