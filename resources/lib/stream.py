# -*- coding: utf-8 -*-
import time
from datetime import datetime

from resources.lib.channels import load_channels
from resources.lib.session import load_session
from resources.lib.epg import get_channel_epg
from resources.lib.api import call_api
from resources.lib.utils import get_config_value

def get_channel_id(channel_name):
    channels = load_channels()
    channel_id = -1
    for channel in channels:
        if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == 'true': 
            if channels[channel]['name'].replace(' HD', '') == channel_name:
                channel_id = channel
        else:
            if channels[channel]['name'] == channel_name:
                channel_id = channel
    return channel_id

def get_live(id):
    token = load_session()
    channels = load_channels()
    for channel in channels:
        if channels[channel]['name'] == id:
            id = channels[channel]['id']
    post = {"payload":{"criteria":{"schema":"ContentCriteria","contentId":"channel." + id},"startMode":"live"},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/content.play', data = post, token = token)
    url = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'
    for asset in data['media']['stream']['assets']:
        if asset['protocol'] == 'hls':
            if 'clear' in asset['src']:
                url = asset['src']
    return url

def get_archive(channel_name, start_ts, end_ts):
    url = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'
    start_ts = int(start_ts)
    end_ts = int(end_ts)
    token = load_session()
    channel_id = get_channel_id(channel_name)
    epg = get_channel_epg(channel_id = channel_id, from_ts = start_ts, to_ts = end_ts + 60*60*12)
    if start_ts in epg:
        if epg[start_ts]['endts'] > int(time.mktime(datetime.now().timetuple()))-10:
            return get_live(channel_name)
        else:
            post = {"payload":{"criteria":{"schema":"ContentCriteria","contentId":epg[start_ts]['id']}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
            data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/content.play', data = post, token = token)
            url = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'
            for asset in data['media']['stream']['assets']:
                if asset['protocol'] == 'hls':
                    if 'clear' in asset['src']:
                        url = asset['src']
            return url            
    else:
        return get_live(channel_name)



