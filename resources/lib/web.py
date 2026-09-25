# -*- coding: utf-8 -*-
import base64
import binascii
import hmac
import json
import os
from urllib.parse import quote, unquote, urlencode
from urllib.error import HTTPError, URLError

from bottle import HTTPResponse, TEMPLATE_PATH, hook, post, request, response, route, run, static_file, template, redirect

from resources.lib.session import Session
from resources.lib.channels import load_channels, load_disabled_channels, save_disabled_channels
from resources.lib.epg import get_epg, load_epg, get_live_epg, get_channel_epg
from resources.lib.stream import get_live, get_archive, rewrite_manifest, FALLBACK_URL, get_channel_id
from resources.lib.utils import get_config_value, get_script_path, get_version, check_client_network, check_ip_whitelist, log_message
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

def handle_manifest(stream, force_proxy=False):
    try:
        return rewrite_manifest(stream, get_base_url(), force_proxy=force_proxy or stream == FALLBACK_URL)
    except HTTPError as e:
        if e.code == 403:
            log_message(f"Chyba 403 při čtení manifestu: {stream}. Zkusím přesměrovat.")            
            return redirect(stream)
        log_message(f"Chyba při čtení manifestu: {e.code} > {e}")
        raise
    except Exception as e:
        log_message(f"Neočekávaná chyba při čtení manifestu: {e}")
        raise e

def add_start_at_begin(lines):
    if not any(line.startswith('#EXTINF:') for line in lines):
        return lines
    lines = [line for line in lines if not line.startswith('#EXT-X-START:')]
    extm3u_idx = next((idx for idx, line in enumerate(lines) if line.startswith('#EXTM3U')), None)
    if extm3u_idx is not None:
        lines.insert(extm3u_idx + 1, '#EXT-X-START:TIME-OFFSET=0,PRECISE=YES')
    return lines

# nalezení navazujícího pořadu v archivu, když aktuální pořad na CDN chybí.
def get_next_archive_stream(channel, query):
    channel_id = get_channel_id(channel)
    if not channel_id:
        return None, 0
    try:
        start_ts = int(query.get('start_ts') or query.get('utc') or 0)
    except ValueError:
        return None, 0
    epg = get_channel_epg(channel_id, start_ts, start_ts + 24 * 60 * 60)
    next_key = next((k for k in sorted(epg) if k > start_ts), None)
    if next_key is None:
        return None, 0
    next_item = epg[next_key]
    next_stream, next_timeshift = get_archive(channel, next_key, next_item['endts'])
    return (next_stream, next_timeshift) if next_stream != FALLBACK_URL else (None, 0)


def parse_archive_query(query):
    has_start_end = 'start_ts' in query or 'end_ts' in query
    has_utc = 'utc' in query or 'lutc' in query
    if not has_start_end and not has_utc:
        return None, None
    if has_start_end and not ('start_ts' in query and 'end_ts' in query):
        return None, 'Parametry start_ts a end_ts musí být uvedeny společně'
    if has_utc and not ('utc' in query and 'lutc' in query):
        return None, 'Parametry utc a lutc musí být uvedeny společně'
    start_name, end_name = ('start_ts', 'end_ts') if has_start_end else ('utc', 'lutc')
    try:
        start_ts = int(query[start_name])
        end_ts = int(query[end_name])
        offset = int(query.get('offset', 0))
    except (TypeError, ValueError):
        return None, 'Archivní parametry musí být celá čísla'
    if start_ts < 0 or end_ts <= start_ts or offset < 0:
        return None, 'Neplatný rozsah archivních parametrů'
    return (start_ts, end_ts, offset), None

@hook('before_request')
def check_basic_auth():
    if request.path == '/health':
        return    
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

@route('/health')
def health():
    return 'OK'

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

@route('/stream/<channel>')
def stream_url(channel):
    try:
        channel = unquote(channel.replace('.m3u8', '')).replace('sleš', '/')
        if channel not in load_channels() and get_channel_id(channel) is None:
            response.content_type = 'application/json'
            response.set_header('Access-Control-Allow-Origin', '*')
            return json.dumps({'url': None, 'error': 'Kanál nenalezen'})        
        archive_params, error = parse_archive_query(request.query)
        if error:
            return HTTPResponse(error, 400)
        if archive_params:
            url, _ = get_archive(channel, archive_params[0], archive_params[1])
        else:
            url = get_live(channel)
        if not url:
            response.content_type = 'application/json'
            response.set_header('Access-Control-Allow-Origin', '*')
            return json.dumps({'url': None, 'error': 'Nepodařilo se získat stream'})
        response.content_type = 'application/json'
        response.set_header('Access-Control-Allow-Origin', '*')
        return json.dumps({'url': url})
    except (Exception, SystemExit) as error:
        response.content_type = 'application/json'
        response.set_header('Access-Control-Allow-Origin', '*')
        response.status = 200
        return json.dumps({'url': None, 'error': str(error) or 'Chyba přihlášení nebo získání streamu'})

# UPRAVENÁ FUNKCE: manifest proxy, timeshift, offset
@route('/play/<channel>')
def play(channel):
    channel = unquote(channel.replace('.m3u8', '')).replace('sleš', '/')
    if channel not in load_channels() and get_channel_id(channel) is None:
        return HTTPResponse('Kanál nenalezen', 404)    
    archive_params, error = parse_archive_query(request.query)
    if error:
        return HTTPResponse(error, 400)
    is_archive_request = archive_params is not None
    if archive_params:
        stream, timeshift = get_archive(channel, *archive_params)
    else:
        stream, timeshift = get_live(channel), 0
    response.content_type = 'application/x-mpegURL'
    try:
        if timeshift > 0:
            return rewrite_manifest(stream, get_base_url(), timeshift)
        return handle_manifest(stream)
    except HTTPError as e:
        if e.code in (502, 503, 504) and is_archive_request:
            # CDN nemá zdroj pro tento pořad (přechod mezi dvěma catchupy) -> zkusit navazující pořad místo pádu na živé vysílání
            next_stream, next_timeshift = get_next_archive_stream(channel, request.query)            
            if next_stream:
                log_message(f"Chyba {e.code} při čtení manifestu: {stream}. Přeskakuji na další pořad v archivu.")
                if next_timeshift > 0:
                    # navazující pořad právě běží živě -> pokračovat od jeho začátku, ne od live okraje
                    return rewrite_manifest(next_stream, get_base_url(), next_timeshift)
                return handle_manifest(next_stream)
            return HTTPResponse(body=str(e), status=e.code)

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
    return play(channel_name)

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
    req = Request(url, headers={'User-Agent': API().UA, 'Accept': '*/*', 'Accept-Encoding': 'gzip'})
    try:
        with urlopen(req, timeout=20) as resp:
            final_url = resp.geturl() or url
            data = resp.read()
            content_encoding = resp.headers.get('Content-Encoding')
            content_type = resp.headers.get('Content-Type', 'application/x-mpegURL')
    except (HTTPError, URLError) as e:
        log_message(f"Chyba proxy_hls při stahování {url}: {e}")
        response.status = 502
        response.content_type = 'application/json'
        return json.dumps({'error': str(e)})
    if content_encoding == 'gzip':    
        data = gzip.decompress(data)
    response.content_type = content_type
    if not (final_url.endswith('.m3u8') or 'mpegURL' in content_type or 'mpegurl' in content_type):    
        return data
    server_base = request.urlparts.scheme + '://' + request.urlparts.netloc
    parsed_parent = _urlparse(final_url)
    parent_query = _parse_qs(parsed_parent.query)
    base_url = final_url.rsplit('/', 1)[0] + '/'
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

    start_at_begin = request.query.get('start_at_begin') == '1'
    start_param = '&start_at_begin=1' if start_at_begin else ''

    def make_proxy_url(uri):
        return f'{server_base}/proxy_hls?url={_urlquote(_merge_url(uri), safe="")}{start_param}'

    text = data.decode('utf-8')
    lines = text.split('\n')
    if start_at_begin:
        lines = add_start_at_begin(lines)

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
    params = ['username', 'password', 'profile', 'deviceid', 'webserver_port', 'epg_dnu_zpetne', 'epg_dnu_dopredu', 'interval_stahovani_epg', 'odstranit_hd', 'pouzivat_cisla_kanalu', 'poradi_sluzby', 'pin', 'debug', 'cesta_ffmpeg', 'auth_user', 'auth_pass']
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
