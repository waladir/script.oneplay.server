# -*- coding: utf-8 -*-
import os

from urllib.parse import quote, unquote
from bottle import run, route, post, response, request, redirect, template, static_file, TEMPLATE_PATH

from resources.lib.session import load_session
from resources.lib.channels import load_channels
from resources.lib.epg import get_epg, load_epg
from resources.lib.stream import get_live, get_archive
from resources.lib.utils import get_config_value, get_script_path, get_version

@route('/epg')
def epg():
    if  int(get_config_value('interval_stahovani_epg')) > 0:
        output = load_epg()
    else:
        output = get_epg()
    response.content_type = 'xml/application; charset=UTF-8'
    return output

@route('/playlist')
def playlist():
    channels = load_channels()
    base_url = request.urlparts.scheme + '://' + request.urlparts.netloc
    output = '#EXTM3U x-tvg-url="' + base_url + '/epg"\n'
    for channel in channels:
        if channels[channel]['logo'] == None:
            logo = ''
        else:
            logo =  channels[channel]['logo']
        if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true':
            channel_name = channels[channel]['name'].replace(' HD', '')
        else:
            channel_name = channels[channel]['name']
        output += '#EXTINF:-1 provider="Oneplay" tvg-chno="' + str(channels[channel]['channel_number']) + '" tvg-name="' + channel_name + '" tvg-logo="' + logo + '" catchup-days="7" catchup="shift", ' + channel_name + '\n'
        if get_config_value('pouzivat_cisla_kanalu') == None or get_config_value('pouzivat_cisla_kanalu') == 0 or get_config_value('pouzivat_cisla_kanalu') == '0' or get_config_value('pouzivat_cisla_kanalu') == 'false':
            output += base_url + '/play/' + quote(channel_name.replace('/', 'sleš')) + '.m3u8\n'
        else:
            output += base_url + '/play_num/' + str(channels[channel]['channel_number']) + '.m3u8\n'
    response.content_type = 'text/plain; charset=UTF-8'
    return output

@route('/playlist/tvheadend')
def playlist_tvheadend():
    channels = load_channels()
    base_url = request.urlparts.scheme + '://' + request.urlparts.netloc
    output = '#EXTM3U x-tvg-url="' + base_url + '/epg"\n'
    ffmpeg = get_config_value('cesta_ffmpeg')
    if ffmpeg == None or len(ffmpeg) == 0:
        ffmpeg = '/usr/bin/ffmpeg'
    for channel in channels:
        if channels[channel]['logo'] == None:
            logo = ''
        else:
            logo =  channels[channel]['logo']
        if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true':
            channel_name = channels[channel]['name'].replace(' HD', '')
        else:
            channel_name = channels[channel]['name']
        output += '#EXTINF:-1 provider="Oneplay" tvg-chno="' + str(channels[channel]['channel_number']) + '" tvg-name="' + channel_name + '" tvg-logo="' + logo + '", ' + channel_name + '\n'
        if get_config_value('pouzivat_cisla_kanalu') == None or get_config_value('pouzivat_cisla_kanalu') == 0 or get_config_value('pouzivat_cisla_kanalu') == '0' or get_config_value('pouzivat_cisla_kanalu') == 'false':
            output += 'pipe://' + ffmpeg + ' -loglevel error -fflags +genpts -i "' + base_url + '/play/' + quote(channel_name.replace('/', 'sleš')) + '.m3u8" -f mpegts -c copy -vcodec copy -acodec copy -metadata service_provider=Oneplay -metadata service_name="' + channel_name + '" pipe:1\n'
        else:
            output += 'pipe://' + ffmpeg + ' -loglevel error -fflags +genpts -i "' + base_url + '/play_num/' + str(channels[channel]['channel_number']) + '.m3u8" -f mpegts -c copy -vcodec copy -acodec copy -metadata service_provider=Oneplay -metadata service_name="' + channel_name + '" pipe:1\n'
    response.content_type = 'text/plain; charset=UTF-8'
    return output

@route('/play/<channel>')
def play(channel):
    channel = unquote(channel.replace('.m3u8', '')).replace('sleš', '/')
    if 'start_ts' in request.query:
        stream = get_archive(channel, request.query['start_ts'], request.query['end_ts'])
    elif 'utc' in request.query:
        stream = get_archive(channel, request.query['utc'], request.query['lutc'])
    else:
        stream = get_live(channel)
    response.content_type = 'application/x-mpegURL'
    return redirect(stream)

@route('/play_num/<channel>')
def play_num(channel):
    channels = load_channels()
    for chan in channels:
        if channels[chan]['channel_number'] == int(channel.replace('.m3u8', '')):
            channel_name = channels[chan]['name']
    if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true':
        channel_name = channel.replace(' HD', '')
    if 'start_ts' in request.query:
        stream = get_archive(channel_name, request.query['start_ts'], request.query['end_ts'])
    elif 'utc' in request.query:
        stream = get_archive(channel_name, request.query['utc'], request.query['lutc'])
    else:
        stream = get_live(channel_name)
    response.content_type = 'application/x-mpegURL'
    return redirect(stream)

@route('/img/<image>')
def add_image(image):
    return static_file(image, root = os.path.join(get_script_path(), 'resources', 'templates'))

@route('/config')
def config():
    config = {}
    params = ['username', 'password', 'profile', 'deviceid', 'webserver_ip', 'webserver_port', 'epg_dnu_zpetne', 'epg_dnu_dopredu', 'interval_stahovani_epg', 'odstranit_hd', 'pouzivat_cisla_kanalu', 'poradi_sluzby', 'pin', 'debug', 'cesta_ffmpeg']
    for param in params:
        if get_config_value(param) is None:
            value = 'není'
        else:
            value = get_config_value(param)
        if param == 'password' and value != 'není':
            config.update({param : '*' * len(value)})
        else:
            config.update({param : value})
    TEMPLATE_PATH.append(os.path.join(get_script_path(), 'resources', 'templates'))
    return template('config.tpl', version = get_version(), config = config)

@route('/')
@post('/')
def page():
    message = ''
    if request.params.get('action') is not None:
        action = request.params.get('action')
        if action == 'reset_channels':
            load_channels(reset = True)
            message = 'Kanály resetovány!'
        elif action == 'reset_session':
            load_session(reset = True)
            message = 'Sessiona resetována!'
    base_url = request.urlparts.scheme + '://' + request.urlparts.netloc
    playlist_url = base_url + '/playlist'
    playlist_tvheadend_url = base_url + '/playlist/tvheadend'
    epg_url = base_url + '/epg'
    playlist = []
    channels = load_channels()
    if get_config_value('pouzivat_cisla_kanalu') == None or get_config_value('pouzivat_cisla_kanalu') == 0 or get_config_value('pouzivat_cisla_kanalu') == '0' or get_config_value('pouzivat_cisla_kanalu') == 'false':
        for channel in channels:
            if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true':
                channel_name = channels[channel]['name'].replace(' HD', '')
            else:
                channel_name = channels[channel]['name']            
            playlist.append({'name' : channel_name, 'url' : base_url + '/play/' + quote(channel_name.replace('/', 'sleš')) + '.m3u8', 'logo' : channels[channel]['logo']})
    else:
        for channel in channels:
            if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true':
                channel_name = channels[channel]['name'].replace(' HD', '')
            else:
                channel_name = channels[channel]['name']            
            playlist.append({'name' : channel_name, 'url' : base_url + '/play_num/' + str(channels[channel]['channel_number']) + '.m3u8', 'logo' : channels[channel]['logo']})
    TEMPLATE_PATH.append(os.path.join(get_script_path(), 'resources', 'templates'))
    return template('form.tpl', version = get_version(), message = message, playlist_url = playlist_url, playlist_tvheadend_url = playlist_tvheadend_url, epg_url = epg_url, playlist = playlist)

def start_server():
    port = int(get_config_value('webserver_port'))
    run(host = '0.0.0.0', port = port)

