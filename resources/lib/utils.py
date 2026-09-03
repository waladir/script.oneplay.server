# -*- coding: utf-8 -*-
# SHARED: Oneplay Server, TVheadend
import ipaddress
import json
import os
import socket
from xml.dom import minidom
from xml.parsers.expat import ExpatError

appVersion = 'R11.33'


def is_docker():
    if os.getenv('container') or os.getenv('DOCKER') or os.path.exists('/.dockerenv'):
        return True
    try:
        with open('/proc/1/cgroup', encoding='utf-8') as file:
            cgroup = file.read()
        return any(name in cgroup for name in ('docker', 'containerd', 'kubepods'))
    except OSError:
        return False


def is_kodi():
    try:
        import xbmc
        int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
        return True
    except Exception:
        return False


def get_script_path():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def get_config_value(setting):
    if is_kodi():
        import xbmcaddon

        return xbmcaddon.Addon().getSetting(setting)

    config_file = os.path.join(get_script_path(), 'config.txt')
    if is_docker() and not os.path.exists(config_file):
        defaults = {
            'WEBSERVER_IP': '0.0.0.0',
            'WEBSERVER_PORT': 8082,
            'EPG_DNU_ZPETNE': 1,
            'EPG_DNU_DOPREDU': 1,
            'INTERVAL_STAHOVANI_EPG': 0,
            'ODSTRANIT_HD': 0,
            'POUZIVAT_CISLA_KANALU': 0,
            'PORADI_SLUZBY': -1,
            'PIN': '4321',
            'PROFILE_PIN': '4321',
            'DEBUG': 0,
            'CESTA_FFMPEG': '/usr/bin/ffmpeg',
            'AUTH_USER': '',
            'AUTH_PASS': '',
        }
        return os.getenv(setting.upper(), defaults.get(setting.upper()))

    with open(config_file, encoding='utf-8') as file:
        return json.load(file).get(setting)


def log_message(message):
    if is_kodi():
        import xbmc

        xbmc.log('Oneplay Server > ' + message)
    else:
        print(message)


def display_message(message, message_type = 'error'):
    if is_kodi():
        import xbmcgui
        xbmcgui.Dialog().notification('Oneplay Server', message, xbmcgui.NOTIFICATION_ERROR, 4000)
    else:
        if message != 'Byla vytvořena nová session':
            print(message)


def display_dialog_yn(heading, message):
    if is_kodi():
        import xbmcgui

        return xbmcgui.Dialog().yesno(heading, message)
    return False


def display_dialog_pin():
    if is_kodi():
        import xbmcgui

        return xbmcgui.Dialog().numeric(type=0, heading='Zadejte PIN', bHiddenInput=True)
    return ''


class Settings:
    def __init__(self):
        if is_kodi():
            import xbmcaddon
            from xbmcvfs import translatePath

            self.addon = xbmcaddon.Addon()
            self.addon_userdata_dir = translatePath(path=self.addon.getAddonInfo('profile'))
        else:
            self.addon_userdata_dir = os.path.join(get_script_path(), 'data')
        os.makedirs(self.addon_userdata_dir, exist_ok=True)

    def save_json_data(self, file_info, data):
        filename = os.path.join(self.addon_userdata_dir, file_info['filename'])
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(f'{data}\n')
        except OSError:
            display_message('Chyba uložení ' + file_info['description'])

    def load_json_data(self, file_info):
        filename = os.path.join(self.addon_userdata_dir, file_info['filename'])
        try:
            with open(filename, encoding='utf-8') as file:
                return file.read().rstrip('\r\n')
        except OSError as error:
            if error.errno != 2:
                display_message('Chyba při načtení ' + file_info['description'])
            return None

    def reset_json_data(self, file_info):
        filename = os.path.join(self.addon_userdata_dir, file_info['filename'])
        try:
            os.remove(filename)
        except OSError:
            pass


def replace_by_html_entity(string):
    return string.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("'", '&apos;').replace('"', '&quot;')

def get_ip_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        connection.connect(('8.8.8.8', 80))
        return connection.getsockname()[0]

def get_version():
    filename = os.path.join(get_script_path(), 'addon.xml')
    try:
        xml = minidom.parse(filename)
        addons = xml.getElementsByTagName('addon')
        if addons:
            return f" (v{addons[0].attributes['version'].value})"
    except (KeyError, OSError, ExpatError):
        pass
    return ''

def check_client_network(ip):
    try:
        server_ip = get_ip_address()
        client_ip = ip
        server_parts = server_ip.split('.')
        client_parts = client_ip.split('.')
        return server_parts[:2] == client_parts[:2] or client_ip == '127.0.0.1' or ipaddress.ip_address(client_ip).is_private
    except Exception:
        return False

def check_ip_whitelist(ip):
    try:
        ip = ipaddress.ip_address((ip or '').strip())
    except ValueError:
        return False
    if ip.is_loopback:
        return True
    ip_whitelist = get_config_value('ip_whitelist')
    if not ip_whitelist or not ip_whitelist.strip():
        return False
    whitelist_items = [item for item in ip_whitelist.replace(' ', '').split(',') if item]
    if not whitelist_items:
        return False
    for item in whitelist_items:
        try:
            network = ipaddress.ip_network(item, strict=True)
            if ip in network:
                return True
        except ValueError:
            continue
    return False
