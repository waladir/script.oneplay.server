# -*- coding: utf-8 -*-
import gzip
import re
import time
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

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
    return url

# NOVÁ FUNKCE: přepis běžného i timeshift HLS manifestu.
def rewrite_manifest(url, server_base_url, offset_seconds=0):
    """Načte master manifest a přepíše URI na absolutní nebo lokálně proxyované."""
    parsed_master = urlparse(url)
    master_query = parse_qs(parsed_master.query)
    headers = {'User-Agent': API().UA, 'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate'}
    with urlopen(Request(url, headers=headers), timeout=20) as manifest_response:
        final_url = manifest_response.geturl() or url
        data = manifest_response.read()
        if manifest_response.headers.get('Content-Encoding') == 'gzip':
            data = gzip.decompress(data)
    base_url = final_url.rsplit('/', 1)[0] + '/'
    lines = data.decode('utf-8').splitlines()
    use_proxy = int(offset_seconds) > 0

    def rewrite_uri(uri):
        absolute_uri = urljoin(base_url, uri)
        parsed_uri = urlparse(absolute_uri)
        query = dict(master_query)
        query.update(parse_qs(parsed_uri.query))
        absolute_uri = urlunparse(parsed_uri._replace(query=urlencode(query, doseq=True)))
        if use_proxy:
            return (server_base_url + '/proxy_hls?url=' + quote(absolute_uri, safe='')
                    + '&ts_offset=' + str(int(offset_seconds)))
        return absolute_uri

    result = []
    for line in lines:
        if 'URI="' in line:
            line = re.sub(
                r'URI="([^"]+)"',
                lambda match: 'URI="' + rewrite_uri(match.group(1)) + '"',
                line,
            )
        result.append(line)
        if line.startswith('#EXTM3U'):
            if use_proxy:
                result.append(f'#EXT-X-START:TIME-OFFSET=-{int(offset_seconds)},PRECISE=YES')
            else:
                result.append('#EXT-X-START:TIME-OFFSET=-3,PRECISE=NO')
        elif line.strip() and not line.startswith('#'):
            result[-1] = rewrite_uri(line.strip())
    return '\n'.join(result)


# UPRAVENÁ FUNKCE: překryv EPG, offset, korekce begin a timeshift živého pořadu.
def get_archive(channel_name, start_ts, end_ts, offset=0):
    url = FALLBACK_URL
    start_ts = int(start_ts)
    end_ts = int(end_ts)
    offset = int(offset)
    api = API()
    session = Session()
    channel_id = get_channel_id(channel_name)
    if not channel_id:
        return get_live(channel_name), 0
    md = '~' in channel_id
    channels = load_channels()
    epg = get_channel_epg(
        channel_id=channel_id,
        from_ts=start_ts - 12 * 60 * 60,
        to_ts=end_ts + 12 * 60 * 60,
    )
    epg_key = next(
        (timestamp for timestamp in sorted(epg) if timestamp <= start_ts < epg[timestamp]['endts']),
        None,
    )
    if epg_key is None:
        return get_live(channel_name), 0

    epg_item = epg[epg_key]
    seek_offset = start_ts - epg_key
    total_offset = offset + seek_offset
    if epg_item['endts'] > int(time.time()) - 10:
        return get_live(channel_name), max(0, int(time.time()) - start_ts)

    if channels[channel_id].get('adult'):
        pin = get_config_value('pin') or '1234'
        deeplink = epg_item.get('payload', {}).get('deeplink', {})
        if not deeplink.get('channel') or not deeplink.get('time'):
            return url, 0
        post = {"authorization":[{"schema":"PinRequestAuthorization","pin":pin,"type":"parental"}],"payload":{"criteria":{'schema': 'ChannelPlaybackCriteria', 'channel': deeplink['channel'], 'time': deeplink['time']}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
    elif md:
        post = {"payload":{"criteria":{"schema":"MDPlaybackCriteria","contentId":epg_item['id'],"position":0}},"playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}
    else:
        detail = api.page_content_display(
            {'payload': epg_item.get('payload') or {}},
            session,
        ) or {}
        payload = detail.get('payload')
        if not payload:
            return url, 0
        post = {"payload":payload, "playbackCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","subtitle":{"formats":["vtt"],"locations":["InstreamTrackLocation","ExternalTrackLocation"]},"liveSpecificCapabilities":{"protocols":["dash","hls"],"drm":["widevine","fairplay"],"altTransfer":"Unicast","multipleAudio":False}}}

    data = api.content_play(post, session) or {}
    media = data.get('media') or {}
    stream = media.get('stream') or {}
    for asset in stream.get('assets') or []:
        if asset.get('protocol') == 'hls' and 'drm' not in asset:
            source = asset.get('src')
            if source and 'free' not in source:
                url = source
            elif source and url == FALLBACK_URL:
                url = source
    if total_offset and 'begin=' in url:
        parsed_url = urlparse(url)
        query = parse_qs(parsed_url.query)
        if 'begin' in query:
            query['begin'] = [str(int(query['begin'][0]) + total_offset)]
            url = urlunparse(parsed_url._replace(query=urlencode(query, doseq=True)))
    return url, 0