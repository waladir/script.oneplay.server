# -*- coding: utf-8 -*-
import os
import socket

import json
from xml.dom import minidom

appVersion = '1.0.10'

def is_docker():
    # Check for Docker-specific environment variables
    docker_env_vars = ['container', 'DOCKER']
    for var in docker_env_vars:
        if os.getenv(var):
            return True
    
    # Check for Docker-specific filesystem paths
    docker_paths = ['/proc/1/cgroup', '/.dockerenv']
    for path in docker_paths:
        if os.path.exists(path):
            return True
    return False

def is_kodi():
    try:
        import xbmc
        test = int(xbmc.getInfoLabel('System.BuildVersion').split('.')[0])
        return True
    except Exception:
        return False

def get_script_path():
    path = os.path.realpath(__file__)
    if path is not None:
        return path.replace('/resources/lib/utils.py', '').replace('\\resources\\lib\\utils.py', '')

def get_config_value(setting):
    if is_kodi() == True:
        import xbmcaddon
        addon = xbmcaddon.Addon()
        return addon.getSetting(setting)
    elif is_docker() == True and not os.path.exists(os.path.join(get_script_path(), 'config.txt')):
        defaults = {'WEBSERVER_IP' : '0.0.0.0', 'WEBSERVER_PORT' : 8082, 'EPG_DNU_ZPETNE' : 1, 'EPG_DNU_DOPREDU' : 1, 'INTERVAL_STAHOVANI_EPG' : 0, 'ODSTRANIT_HD' : 0, 'POUZIVAT_CISLA_KANALU' : 0, 'PORADI_SLUZBY' : -1, 'PIN' : '4321', 'DEBUG' : 0, 'CESTA_FFMPEG' : '/usr/bin/ffmpeg'} 
        value = os.getenv(setting.upper())
        if value is None and setting.upper() in defaults:
            value = defaults[setting.upper()]
        return value
    else:
        config_file = os.path.join(get_script_path(), 'config.txt')
        with open(config_file, 'r') as f:
            config = json.load(f)
            f.close()
        if setting in config:
            return config[setting]

def log_message(message):
    if is_kodi() == True:
        import xbmc
        xbmc.log('Oneplay Server > ' + message) 
    else:
        print(message)

def display_message(message):
    if is_kodi() == True:
        import xbmcgui
        xbmcgui.Dialog().notification('Oneplay Server', message, xbmcgui.NOTIFICATION_ERROR, 4000)
    else:
        print(message)

def save_json_data(file, data):
    if is_kodi() == True:
        import xbmcaddon
        from xbmcvfs import translatePath
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
    else:
        addon_userdata_dir = os.path.join(get_script_path(), 'data')
    filename = os.path.join(addon_userdata_dir, file['filename'])
    try:
        with open(filename, "w") as f:
            f.write('%s\n' % data)
    except IOError:
        display_message('Chyba uložení ' + file['description'])

def load_json_data(file):
    data = None
    if is_kodi() == True:
        import xbmcaddon
        from xbmcvfs import translatePath
        addon = xbmcaddon.Addon()
        addon_userdata_dir = translatePath(addon.getAddonInfo('profile'))
    else:
        addon_userdata_dir = os.path.join(get_script_path(), 'data')
    filename = os.path.join(addon_userdata_dir, file['filename'])
    try:
        with open(filename, "r") as f:
            for row in f:
                data = row[:-1]
    except IOError as error:
        if error.errno != 2:
            display_message('Chyba při načtení ' + file['description'])
    return data    

def replace_by_html_entity(string):
    return string.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace("'","&apos;").replace('"',"&quot;")

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def get_version():
    version = ''
    filename = os.path.join(get_script_path(), 'addon.xml')    
    try:
        xml = minidom.parse(filename)
        addon = xml.getElementsByTagName('addon')
        for element in addon:
            version = ' (v.' + element.attributes['version'].value + ')'
    except IOError as error:
        return version
    return version
