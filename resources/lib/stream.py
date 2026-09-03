# -*- coding: utf-8 -*-
import time

from resources.lib.channels import load_channels
from resources.lib.session import Session
from resources.lib.api import API
from resources.lib.epg import get_channel_epg
from resources.lib.utils import get_config_value

FALLBACK_URL = 'http://sledovanietv.sk/download/noAccess-cs.m3u8'


def get_channel_id(channel_name):
    channels = load_channels()
    remove_hd = get_config_value('odstranit_hd') in (1, '1', 'true')
    for channel_id, channel in channels.items():
        name = channel['name'].replace(' HD', '') if remove_hd else channel['name']
        if name == channel_name:
            return channel_id
    return None

def get_live(id):
    api = API()
    session = Session()
    channels = load_channels()
    id = id if id in channels else get_channel_id(id)
    if not id:
        return FALLBACK_URL
    selected_channel = channels[id]
    if '~' in id:
        md = True
        channel = id.split('~', 1)
        id = channel[0]
        md_stream = int(channel[1])
    else:
        md = False

    if selected_channel.get('adult'):
        pin = get_config_value('pin') or '1234'
        post = {"authorization":[{"schema":"PinRequestAuthorization","pin":pin,"type":"parental"}],"payload":{"criteria":{"schema":"ContentCriteria","contentId":"channel." + id},"startMode":"start"},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
    else:
        post = {"payload":{"criteria":{"schema":"ContentCriteria","contentId":"channel." + id},"startMode":"start"},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
    data = api.content_play(post, session) or {}
    if 'media' not in data:
        post['payload']['startMode'] = 'live'
        data = api.content_play(post, session) or {}
    player_control = data.get('playerControl') or {}
    live_control = player_control.get('liveControl') or {}
    if md and live_control.get('mosaic'):
        stream_number = 1
        for md_item in live_control['mosaic'].get('items') or []:
            if md_stream == stream_number:
                md_payload = md_item.get('play', {}).get('params', {}).get('payload') or {}
                md_id = md_payload.get('criteria', {}).get('contentId') or md_payload.get('contentId')
                if md_id is not None:
                    post = {"payload":{"criteria":{"schema":"MDPlaybackCriteria","contentId":md_id,"position":0},"startMode":"start"},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
                    data = api.content_play(post, session) or {}
                    if 'media' not in data:
                        return FALLBACK_URL
            stream_number += 1
    url = FALLBACK_URL
    player_control = data.get('playerControl') or {}
    live_control = player_control.get('liveControl') or {}
    if live_control.get('channelId') and live_control.get('timeline'):
        if live_control['timeline'].get('timeShift', {}).get('available') is False:
            post['payload'] = {'criteria': post['payload']['criteria'], 'startMode': 'live'}
            data = api.content_play(post, session) or {}
    media = data.get('media') or {}
    stream = media.get('stream') or {}
    for asset in stream.get('assets') or []:
        if asset.get('protocol') == 'hls':
            if 'drm' not in asset:
                source = asset.get('src')
                if source and 'clear' not in source:
                    url = source
                elif source and url == FALLBACK_URL:
                    url = source
    print(url)
    return url

def get_archive(channel_name, start_ts, end_ts):
    url = FALLBACK_URL
    start_ts = int(start_ts)
    end_ts = int(end_ts)
    api = API()
    session = Session()
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        return get_live(channel_name)
    md = '~' in channel_id
    channels = load_channels()
    epg = get_channel_epg(
        channel_id=channel_id,
        from_ts=start_ts,
        to_ts=end_ts + 12 * 60 * 60,
    )
    if start_ts in epg:
        epg_item = epg[start_ts]
        if epg_item['endts'] > int(time.time()) - 10:
            return get_live(channel_name)
        else:
            if channels[channel_id].get('adult'):
                pin = get_config_value('pin') or '1234'
                deeplink = epg_item.get('payload', {}).get('deeplink', {})
                if not deeplink.get('channel') or not deeplink.get('time'):
                    return url
                post = {"authorization":[{"schema":"PinRequestAuthorization","pin":pin,"type":"parental"}],"payload":{"criteria":{'schema': 'ChannelPlaybackCriteria', 'channel': deeplink['channel'], 'time': deeplink['time']}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
            else:
                if md:
                    post = {"payload":{"criteria":{"schema":"MDPlaybackCriteria","contentId":epg_item['id'],"position":0}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
                else:
                    detail = api.page_content_display(
                        {'payload': epg_item.get('payload') or {}},
                        session,
                    ) or {}
                    payload = detail.get('payload')
                    if not payload:
                        return url
                    post = {"payload":payload, "playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}                                        
            data = api.content_play(post, session) or {}
            media = data.get('media') or {}
            stream = media.get('stream') or {}
            for asset in stream.get('assets') or []:
                if asset.get('protocol') == 'hls':
                    if 'drm' not in asset:
                        source = asset.get('src')
                        if source and 'free' not in source:
                            url = source
                        elif source and url == FALLBACK_URL:
                            url = source
            return url
    else:
        return get_live(channel_name)
