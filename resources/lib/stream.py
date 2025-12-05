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
        if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true': 
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
        if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true': 
            if channels[channel]['name'].replace(' HD', '') == id:
                id = channels[channel]['id']
        else:
            if channels[channel]['name'] == id:
                id = channels[channel]['id']
    if '~' in id:
        md = True
        channel = id.split('~')
        id = channel[0]
        md_stream = int(channel[1])
    else:
        md = False

    if channels[id]['adult'] == True:
        if get_config_value('pin') is not None and len(get_config_value('pin')) > 0:
            pin = get_config_value('pin')
        else:
            pin = '1234'
        post = {"authorization":[{"schema":"PinRequestAuthorization","pin":pin,"type":"parental"}],"payload":{"criteria":{"schema":"ContentCriteria","contentId":"channel." + id},"startMode":"start"},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
    else:
        post = {"payload":{"criteria":{"schema":"ContentCriteria","contentId":"channel." + id},"startMode":"start"},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v1.6/content.play', data = post, token = token)
    if md == True and 'liveControl' in data['playerControl'] and 'mosaic' in data['playerControl']['liveControl']:
        stream_number = 1
        for md_item in data['playerControl']['liveControl']['mosaic']['items']:
            if md_stream == stream_number:
                md_id = None
                if 'criteria' in md_item['play']['params']['payload'] and 'contentId' in md_item['play']['params']['payload']['criteria']:
                    md_id = md_item['play']['params']['payload']['criteria']['contentId']
                elif 'contentId' in md_item['play']['params']['payload']:
                    md_id = md_item['play']['params']['payload']['contentId']
                if md_id is not None:
                    post = {"payload":{"criteria":{"schema":"MDPlaybackCriteria","contentId":md_id,"position":0},"startMode":"start"},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
                    data = call_api(url = 'https://http.cms.jyxo.cz/api/v1.6/content.play', data = post, token = token)
                    if 'err' in data or 'media' not in data:
                        url = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'
                        return url
            stream_number = stream_number + 1
    url = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'
    if 'playerControl' in data and 'liveControl' in data['playerControl'] and 'channelId' in data['playerControl']['liveControl'] and 'timeline' in data['playerControl']['liveControl']:
        if 'timeShift' in data['playerControl']['liveControl']['timeline'] and data['playerControl']['liveControl']['timeline']['timeShift']['available'] == False:
            post.update({'payload' : {'criteria' : post['payload']['criteria'], 'startMode' : 'live'}})
            data = call_api(url = 'https://http.cms.jyxo.cz/api/v1.6/content.play', data = post, token = token)
    for asset in data['media']['stream']['assets']:
        if asset['protocol'] == 'hls':
            if 'drm' not in asset:
                if 'clear' not in asset['src']:
                    url = asset['src']
                elif url == 'http://sledovanietv.sk/download/noAccess-cs.m3u8':
                    url = asset['src']
    return url

def get_archive(channel_name, start_ts, end_ts):
    url = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'
    start_ts = int(start_ts)
    end_ts = int(end_ts)
    token = load_session()
    channel_id = get_channel_id(channel_name)
    if '~' in channel_id:
        md = True
    else:
        md = False
    channels = load_channels()
    epg = get_channel_epg(channel_id = channel_id, from_ts = start_ts, to_ts = end_ts + 60*60*12)
    if start_ts in epg:
        if epg[start_ts]['endts'] > int(time.mktime(datetime.now().timetuple()))-10:
            return get_live(channel_name)
        else:
            if channels[channel_id]['adult'] == True:
                if get_config_value('pin') is not None and len(get_config_value('pin')) > 0:
                    pin = get_config_value('pin')
                else:
                    pin = '1234'
                post = {"authorization":[{"schema":"PinRequestAuthorization","pin":pin,"type":"parental"}],"payload":{"criteria":{"schema":"ContentCriteria","contentId":epg[start_ts]['id']}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
            else:
                if md == True:
                    post = {"payload":{"criteria":{"schema":"MDPlaybackCriteria","contentId":epg[start_ts]['id'],"position":0}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
                else:
                    post = {"payload":{"criteria":{"schema":"ContentCriteria","contentId":epg[start_ts]['id']}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}                                        
            data = call_api(url = 'https://http.cms.jyxo.cz/api/v1.6/content.play', data = post, token = token)
            url = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'
            for asset in data['media']['stream']['assets']:
                if asset['protocol'] == 'hls':
                    if 'drm' not in asset:
                        if 'free' not in asset['src']:
                            url = asset['src']
                        elif url == 'http://sledovanietv.sk/download/noAccess-cs.m3u8':
                            url = asset['src']
            return url            
    else:
        return get_live(channel_name)



