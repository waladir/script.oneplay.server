# -*- coding: utf-8 -*-
import sys
import time
from datetime import datetime
import threading

from resources.lib.web import start_server
from resources.lib.epg import load_epg
from resources.lib.utils import is_kodi, get_config_value, log_message

class BottleThreadClass(threading.Thread):
    def run(self):
        start_server()

if is_kodi() == True:
    time.sleep(20)
    
bt = BottleThreadClass()
bt.start()

tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)
if int(get_config_value('interval_stahovani_epg')) == 0:
    sys.exit()

next = time.time() + 10
if is_kodi() == True:
    import xbmc
    while not xbmc.Monitor().abortRequested():
        if(next < time.time()):
            time.sleep(3)
            if get_config_value('username') and len(get_config_value('username')) > 0 and get_config_value('password') and len(get_config_value('password')) > 0:
                if int(get_config_value('interval_stahovani_epg')) > 0:
                    load_epg(reset = True)
                    interval = int(get_config_value('interval_stahovani_epg'))*60
                    next = time.time() + float(interval)
        time.sleep(1)
else:
    try:
        log_message('Start plánovače pro stahování EPG\n')
        while True:
            if(next < time.time()):
                time.sleep(3)
                if get_config_value('username') and len(get_config_value('username')) > 0 and get_config_value('password') and len(get_config_value('password')) > 0:
                    if int(get_config_value('interval_stahovani_epg')) > 0:
                        log_message('Začátek stahování EPG\n')
                        load_epg(reset = True)
                        log_message('Konec stahování EPG\n')
                        interval = int(get_config_value('interval_stahovani_epg'))*60*60
                        next = time.time() + float(interval)
            time.sleep(1)
    except KeyboardInterrupt:
        log_message('Ukončení plánovače pro stahování EPG\n')
