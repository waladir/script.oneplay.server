# -*- coding: utf-8 -*-
import base64
import binascii
import hmac
import json
import os
from urllib.parse import quote, unquote, urlencode

from bottle import HTTPResponse, TEMPLATE_PATH, hook, post, request, response, route, run, static_file, template

from resources.lib.session import Session
from resources.lib.channels import load_channels, load_disabled_channels, save_disabled_channels
from resources.lib.epg import get_epg, load_epg, get_live_epg, get_channel_epg
from resources.lib.stream import get_live, get_archive, rewrite_manifest
from resources.lib.utils import get_config_value, get_script_path, get_version, check_client_network, check_ip_whitelist
from resources.lib.api import API


def get_base_url(include_auth=False):
    base_url = request.urlparts.scheme + '://' + request.urlparts.netloc
    if not include_auth:
        return base_url
    auth_user = get_config_value('auth_user')
    auth_pass = get_config_value('auth_pass')
    if not auth_user or not auth_pass:
        return base_url
    auth_prefix = quote(auth_user, safe='') + ':' + quote(auth_pass, safe='') + '@'
    return request.urlparts.scheme + '://' + auth_prefix + request.urlparts.netloc


@hook('before_request')
def check_basic_auth():
    auth_user = get_config_value('auth_user')
    auth_pass = get_config_value('auth_pass')
    if not auth_user or not auth_pass:
        return
    if check_ip_whitelist(request.environ.get('REMOTE_ADDR', '')):
        return
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Basic '):
        try:
            decoded = base64.b64decode(auth[6:], validate=True).decode('utf-8')
            username, password = decoded.split(':', 1)
            if hmac.compare_digest(username, auth_user) and hmac.compare_digest(password, auth_pass):
                return
        except (binascii.Error, UnicodeDecodeError, ValueError):
            pass
    err = HTTPResponse('Přístup odepřen', 401)
    err.set_header('WWW-Authenticate', 'Basic realm="Oneplay Server"')
    raise err

@route('/epg')
def epg():
    if int(get_config_value('interval_stahovani_epg')) > 0:
        output = load_epg()
    else:
        output = get_epg()
    response.content_type = 'application/xml; charset=UTF-8'
    return output

@route('/epg_live')
def epg_now():
    epg_by_channel = get_live_epg()
    result = {
        channel_id: epg_data['now']
        for channel_id, epg_data in epg_by_channel.items()
        if epg_data['now'] is not None
    }
    response.content_type = 'application/json'
    response.set_header('Access-Control-Allow-Origin', '*')
    return json.dumps(result)

@route('/epg_channel/<channel_id>/<day_offset:int>')
def epg_channel(channel_id, day_offset):
    from datetime import datetime as dt
    import time as t
    today = dt.today()
    day_start = int(t.mktime(dt(today.year, today.month, today.day).timetuple())) + day_offset * 86400
    day_end = day_start + 86400 - 1
    epg = get_channel_epg(channel_id, day_start, day_end)
    result = []
    for ts in sorted(epg):
        item = epg[ts]
        result.append({
            'title': item['title'],
            'description': item.get('description', ''),
            'startts': item['startts'],
            'endts': item['endts'],
            'cover': item.get('cover', '')
        })
    response.content_type = 'application/json'
    response.set_header('Access-Control-Allow-Origin', '*')
    return json.dumps(result)

@route('/playlist')
@route('/playlist/group/<group_name>')
def playlist(group_name=None):
    headers = {'User-Agent': API().UA, 'Accept-Encoding': 'gzip, deflate, br, zstd', 'Accept': '*/*'}
    encoded_headers = urlencode(headers)
    channels = load_channels()
    base_url = get_base_url()
    output = '#EXTM3U x-tvg-url="' + base_url + '/epg"\n'
    group_string = f' group-title="{group_name}"' if group_name else ''
    remove_hd = get_config_value('odstranit_hd') in (1, '1', 'true')
    use_numbers = get_config_value('pouzivat_cisla_kanalu') not in (None, 0, '0', 'false')
    for channel in channels.values():
        if channel.get('visible'):
            logo = channel.get('logo') or ''
            channel_name = channel['name'].replace(' HD', '') if remove_hd else channel['name']
            output += '#EXTINF:-1 provider="Oneplay" tvg-chno="' + str(channel['channel_number']) + '" tvg-name="' + channel_name + '" tvg-logo="' + logo + '"' + group_string + ' catchup-days="7" catchup="shift", ' + channel_name + '\n'
            output += '#KODIPROP:inputstream.adaptive.stream_headers=' + encoded_headers + '\n'
            output += '#KODIPROP:inputstream.adaptive.manifest_headers=' + encoded_headers + '\n'
            if not use_numbers:
                output += base_url + '/play/' + quote(channel_name.replace('/', 'sleš')) + '.m3u8\n'
            else:
                output += base_url + '/play_num/' + str(channel['channel_number']) + '.m3u8\n'
    response.content_type = 'text/plain; charset=UTF-8'
    return output

@route('/playlist/tvheadend')
def playlist_tvheadend():
    user_agent = API().UA
    channels = load_channels()
    base_url = get_base_url()
    output = '#EXTM3U x-tvg-url="' + base_url + '/epg"\n'
    ffmpeg = get_config_value('cesta_ffmpeg') or '/usr/bin/ffmpeg'
    remove_hd = get_config_value('odstranit_hd') in (1, '1', 'true')
    use_numbers = get_config_value('pouzivat_cisla_kanalu') not in (None, 0, '0', 'false')
    for channel in channels.values():
        if channel.get('visible'):
            logo = channel.get('logo') or ''
            channel_name = channel['name'].replace(' HD', '') if remove_hd else channel['name']
            output += '#EXTINF:-1 provider="Oneplay" tvg-chno="' + str(channel['channel_number']) + '" tvg-name="' + channel_name + '" tvg-logo="' + logo + '", ' + channel_name + '\n'
            if not use_numbers:
                output += 'pipe://' + ffmpeg + ' -loglevel error -fflags +genpts -user_agent "'+ user_agent + '" -i "' + base_url + '/play/' + quote(channel_name.replace('/', 'sleš')) + '.m3u8" -f mpegts -c copy -vcodec copy -acodec copy -metadata service_provider=Oneplay -metadata service_name="' + channel_name + '" pipe:1\n'
            else:
                output += 'pipe://' + ffmpeg + ' -loglevel error -fflags +genpts -user_agent "'+ user_agent + '" -i "' + base_url + '/play_num/' + str(channel['channel_number']) + '.m3u8" -f mpegts -c copy -vcodec copy -acodec copy -metadata service_provider=Oneplay -metadata service_name="' + channel_name + '" pipe:1\n'
    response.content_type = 'text/plain; charset=UTF-8'
    return output

# UPRAVENÁ FUNKCE: kompatibilní endpoint /stream a nové návratové rozhraní archivu.
@route('/stream/<channel>')
@route('/stream_url/<channel>')
def stream_url(channel):
    try:
        channel = unquote(channel.replace('.m3u8', '')).replace('sleš', '/')
        if 'start_ts' in request.query and 'end_ts' in request.query:
            url, _ = get_archive(channel, request.query['start_ts'], request.query['end_ts'])
        elif 'utc' in request.query and 'lutc' in request.query:
            url, _ = get_archive(channel, request.query['utc'], request.query['lutc'])
        else:
            url = get_live(channel)
        if not url:
            response.content_type = 'application/json'
            response.set_header('Access-Control-Allow-Origin', '*')
            return json.dumps({'url': None, 'error': 'Nepodařilo se získat stream'})
        response.content_type = 'application/json'
        response.set_header('Access-Control-Allow-Origin', '*')
        return json.dumps({'url': url})
    except Exception as error:
        response.content_type = 'application/json'
        response.set_header('Access-Control-Allow-Origin', '*')
        response.status = 200
        return json.dumps({'url': None, 'error': str(error)})

# UPRAVENÁ FUNKCE: manifest proxy, timeshift, offset
@route('/play/<channel>')
def play(channel):
    channel = unquote(channel.replace('.m3u8', '')).replace('sleš', '/')
    offset = request.query.get('offset', 0)
    if 'start_ts' in request.query and 'end_ts' in request.query:
        stream, timeshift = get_archive(channel, request.query['start_ts'], request.query['end_ts'], offset)
    elif 'utc' in request.query and 'lutc' in request.query:
        stream, timeshift = get_archive(channel, request.query['utc'], request.query['lutc'], offset)
    else:
        stream, timeshift = get_live(channel), 0
    response.content_type = 'application/x-mpegURL'
    if timeshift > 0:
        return rewrite_manifest(stream, get_base_url(), timeshift)
    return rewrite_manifest(stream, get_base_url())

# UPRAVENÁ FUNKCE: číselné ID kanálu, manifest proxy, timeshift, offset
@route('/play_num/<channel>')
def play_num(channel):
    channels = load_channels()
    try:
        channel_number = int(channel.replace('.m3u8', ''))
    except ValueError:
        return HTTPResponse('Kanál nenalezen', 404)
    channel_name = next((item['name'] for item in channels.values() if item['channel_number'] == channel_number), None)
    if channel_name is None:
        return HTTPResponse('Kanál nenalezen', 404)
    if get_config_value('odstranit_hd') in (1, '1', 'true'):
        channel_name = channel_name.replace(' HD', '')
    offset = request.query.get('offset', 0)
    if 'start_ts' in request.query and 'end_ts' in request.query:
        stream, timeshift = get_archive(channel_name, request.query['start_ts'], request.query['end_ts'], offset)
    elif 'utc' in request.query and 'lutc' in request.query:
        stream, timeshift = get_archive(channel_name, request.query['utc'], request.query['lutc'], offset)
    else:
        stream, timeshift = get_live(channel_name), 0
    response.content_type = 'application/x-mpegURL'
    if timeshift > 0:
        return rewrite_manifest(stream, get_base_url(), timeshift)
    return rewrite_manifest(stream, get_base_url())

# NOVÁ FUNKCE: proxy HLS playlistů a segmentů pro timeshift.
@route('/proxy_hls')
def proxy_hls():
    from urllib.request import urlopen, Request
    from urllib.parse import urljoin as _urljoin, quote as _urlquote, urlparse as _urlparse, parse_qs as _parse_qs, urlencode as _urlencode, urlunparse as _urlunparse
    import gzip
    import re
    url = request.query.get('url', '')
    if not url:
        response.status = 400
        return 'Missing url parameter'
    req = Request(url, headers={'User-Agent': API().UA, 'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate'})
    resp = urlopen(req)
    data = resp.read()
    if resp.headers.get('Content-Encoding') == 'gzip':
        data = gzip.decompress(data)
    content_type = resp.headers.get('Content-Type', 'application/x-mpegURL')
    response.content_type = content_type
    if not (url.endswith('.m3u8') or 'mpegURL' in content_type or 'mpegurl' in content_type):
        return data
    server_base = request.urlparts.scheme + '://' + request.urlparts.netloc
    parsed_parent = _urlparse(url)
    parent_query = _parse_qs(parsed_parent.query)
    base_url = url.rsplit('/', 1)[0] + '/'
    base_url = base_url.split('?')[0]
    if not base_url.endswith('/'):
        base_url += '/'

    def _merge_url(uri):
        if not uri.startswith('http'):
            uri = _urljoin(base_url, uri)
        parsed = _urlparse(uri)
        sub_params = _parse_qs(parsed.query)
        merged = dict(parent_query)
        merged.update(sub_params)
        return _urlunparse(parsed._replace(query=_urlencode(merged, doseq=True)))

    ts_offset = request.query.get('ts_offset', '')
    ts_param = f'&ts_offset={ts_offset}' if ts_offset else ''

    def make_proxy_url(uri):
        return f'{server_base}/proxy_hls?url={_urlquote(_merge_url(uri), safe="")}{ts_param}'

    text = data.decode('utf-8')
    lines = text.split('\n')

    # If ts_offset is set, convert live playlist to VOD starting at the desired position
    if ts_offset and '#EXTINF' in text:
        offset_secs = int(ts_offset)
        segments = []
        i = 0
        while i < len(lines):
            if lines[i].startswith('#EXTINF:'):
                try:
                    dur = float(lines[i].split(':')[1].split(',')[0])
                except (ValueError, IndexError):
                    dur = 0
                seg_start = i
                seg_end = i + 1
                if seg_end < len(lines) and lines[seg_end].strip() and not lines[seg_end].startswith('#'):
                    seg_end += 1
                segments.append((seg_start, seg_end, dur))
                i = seg_end
            else:
                i += 1
        if segments:
            total = sum(s[2] for s in segments)
            skip_duration = total - offset_secs
            if skip_duration > 0:
                cumulative = 0
                first_keep = 0
                for idx, (start, end, dur) in enumerate(segments):
                    cumulative += dur
                    if cumulative >= skip_duration:
                        first_keep = idx
                        break
                if first_keep > 0:
                    cut_line = segments[first_keep][0]
                    header = lines[:segments[0][0]]
                    updated_header = []
                    for h in header:
                        if h.startswith('#EXT-X-MEDIA-SEQUENCE:'):
                            try:
                                orig_seq = int(h.split(':')[1].strip())
                                updated_header.append(f'#EXT-X-MEDIA-SEQUENCE:{orig_seq + first_keep}')
                            except (ValueError, IndexError):
                                updated_header.append(h)
                        else:
                            updated_header.append(h)
                    lines = updated_header + lines[cut_line:]
        # Always mark as VOD so player starts from first segment
        if not any(l.strip() == '#EXT-X-ENDLIST' for l in lines):
            lines.append('#EXT-X-ENDLIST')

    result = []
    for line in lines:
        if 'URI="' in line:
            def replace_uri(match):
                return f'URI="{make_proxy_url(match.group(1))}"'
            line = re.sub(r'URI="([^"]+)"', replace_uri, line)
        result.append(line)
        if line.strip() and not line.startswith('#'):
            uri = line.strip()
            if uri.endswith('.m3u8') or '.m3u8?' in uri:
                result[-1] = make_proxy_url(uri)
            else:
                result[-1] = _merge_url(uri)
    return '\n'.join(result)


@route('/img/<image>')
def add_image(image):
    return static_file(image, root=os.path.join(get_script_path(), 'resources', 'templates'))

@route('/config')
def config():
    config = {}
    params = ['username', 'password', 'profile', 'deviceid', 'webserver_ip', 'webserver_port', 'epg_dnu_zpetne', 'epg_dnu_dopredu', 'interval_stahovani_epg', 'odstranit_hd', 'pouzivat_cisla_kanalu', 'poradi_sluzby', 'pin', 'debug', 'cesta_ffmpeg', 'auth_user', 'auth_pass']
    for param in params:
        value = get_config_value(param)
        value = 'není' if value is None else value
        if param in ['password', 'auth_pass'] and value != 'není':
            config[param] = '*' * len(str(value))
        else:
            config[param] = value
    response.content_type = 'application/json'
    return json.dumps(config)

@route('/channel/<channel>/<status>')
def channel(channel, status):
    disabled_channels = set(load_disabled_channels())

    if status == "disable":
        disabled_channels.add(channel)
    elif status == "enable":
        disabled_channels.discard(channel)

    save_disabled_channels(list(disabled_channels))

@route('/')
@post('/')
def page():
    message = ''
    ip = request.environ.get('REMOTE_ADDR', '')
    warning = not check_client_network(ip) and not check_ip_whitelist(ip)
    if request.params.get('action') is not None:
        action = request.params.get('action')
        if action == 'reset_channels':
            load_channels(reset = True)
            message = 'Kanály resetovány!'
        elif action == 'reset_session':
            session = Session()
            session.remove_session()
            message = 'Sessiona resetována!'
    auth_enabled = bool(get_config_value('auth_user') and get_config_value('auth_pass'))
    player_enabled = auth_enabled or not warning
    base_url_with_auth = get_base_url(include_auth = True)
    playlist_url = base_url_with_auth + '/playlist'
    playlist_tvheadend_url = base_url_with_auth + '/playlist/tvheadend'
    epg_url = base_url_with_auth + '/epg'
    playlist = []
    channels = load_channels()
    remove_hd = get_config_value('odstranit_hd') in (1, '1', 'true')
    use_numbers = get_config_value('pouzivat_cisla_kanalu') not in (None, 0, '0', 'false')
    for channel_id, channel in channels.items():
        channel_name = channel['name'].replace(' HD', '') if remove_hd else channel['name']
        slug = quote(channel_name.replace('/', 'sleš')) + '.m3u8'
        if use_numbers:
            url = base_url_with_auth + '/play_num/' + str(channel['channel_number']) + '.m3u8'
        else:
            url = base_url_with_auth + '/play/' + slug
        playlist.append({
            'name': channel_name,
            'url': url,
            'slug': slug,
            'logo': channel['logo'],
            'channel_id': channel_id,
            'liveOnly': channel.get('liveOnly', False),
            'visible': channel['visible'],
        })
    template_path = os.path.join(get_script_path(), 'resources', 'templates')
    if template_path not in TEMPLATE_PATH:
        TEMPLATE_PATH.append(template_path)
    return template(
        'form.tpl',
        version=get_version(),
        message=message,
        warning=warning,
        playlist_url=playlist_url,
        playlist_tvheadend_url=playlist_tvheadend_url,
        epg_url=epg_url,
        playlist=playlist,
        auth_enabled=auth_enabled,
        player_enabled=player_enabled,
    )

def start_server():
    port = int(get_config_value('webserver_port'))
    run(host='0.0.0.0', port=port)
