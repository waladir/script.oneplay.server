# -*- coding: utf-8 -*-
import sys
import threading
import time

from resources.lib.epg import load_epg
from resources.lib.utils import is_kodi, get_config_value, log_message
from resources.lib.web import start_server


class BottleThreadClass(threading.Thread):
    def run(self):
        start_server()


kodi = is_kodi()
if kodi:
    time.sleep(20)

server_thread = BottleThreadClass()
server_thread.start()

if int(get_config_value('interval_stahovani_epg')) == 0:
    sys.exit()

next_download = time.time() + 10
if kodi:
    import xbmc

    while not xbmc.Monitor().abortRequested():
        if next_download < time.time():
            time.sleep(3)
            username = get_config_value('username')
            password = get_config_value('password')
            interval = int(get_config_value('interval_stahovani_epg'))
            if username and password and interval > 0:
                load_epg(reset=True)
                next_download = time.time() + interval * 60 * 60
            else:
                next_download = time.time() + 60
        time.sleep(1)
else:
    try:
        log_message('Start plánovače pro stahování EPG\n')
        while True:
            if next_download < time.time():
                time.sleep(3)
                username = get_config_value('username')
                password = get_config_value('password')
                interval = int(get_config_value('interval_stahovani_epg'))
                if username and password and interval > 0:
                    log_message('Začátek stahování EPG\n')
                    load_epg(reset=True)
                    log_message('Konec stahování EPG\n')
                    next_download = time.time() + interval * 60 * 60
                else:
                    next_download = time.time() + 60
            time.sleep(1)
    except KeyboardInterrupt:
        log_message('Ukončení plánovače pro stahování EPG\n')
