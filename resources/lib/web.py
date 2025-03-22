# -*- coding: utf-8 -*-
import os

from urllib.parse import quote, unquote
from bottle import run, route, post, response, request, redirect, template, static_file, TEMPLATE_PATH

from resources.lib.session import load_session
from resources.lib.channels import load_channels
from resources.lib.epg import get_epg, load_epg
from resources.lib.stream import get_live, get_archive
from resources.lib.utils import get_config_value, get_script_path, get_ip_address

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
    output = '#EXTM3U\n'
    base_url = request.urlparts.scheme + '://' + request.urlparts.netloc
    output += '" url-tvg="' + base_url + '/epg\n'
    for channel in channels:
        if channels[channel]['logo'] == None:
            logo = ''
        else:
            logo =  channels[channel]['logo']
        if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == '1' or get_config_value('odstranit_hd') == 'true':
            channel_name = channels[channel]['name'].replace(' HD', '')
        else:
            channel_name = channels[channel]['name']
        output += '#EXTINF:-1 provider="Oneplay" tvg-chno="' + str(channels[channel]['channel_number']) + '" tvg-name="' + channel_name + '" tvg-logo="' + logo + '" catchup-days="7" catchup="append" catchup-source="?start_ts={utc}&end_ts={utcend}", ' + channel_name + '\n'
        if get_config_value('pouzivat_cisla_kanalu') == None or get_config_value('pouzivat_cisla_kanalu') == 0 or get_config_value('pouzivat_cisla_kanalu') == '0' or get_config_value('pouzivat_cisla_kanalu') == 'false':
            output += base_url + '/play/' + quote(channel_name.replace('/', 'sleš')) + '.m3u8\n'
        else:
            output += base_url + '/play_num/' + str(channels[channel]['channel_number']) + '.m3u8\n'
    response.content_type = 'text/plain; charset=UTF-8'
    return output

@route('/playlist/tvheadend')
def playlist_tvheadend():
    channels = load_channels()
    output = '#EXTM3U\n'
    ffmpeg = get_config_value('cesta_ffmpeg')
    base_url = request.urlparts.scheme + '://' + request.urlparts.netloc
    output += '" url-tvg="' + base_url + '/epg\n'
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
    else:
        stream = get_live(channel_name)
    response.content_type = 'application/x-mpegURL'
    return redirect(stream)

@route('/img/<image>')
def add_image(image):
    return static_file(image, root = os.path.join(get_script_path(), 'resources', 'templates'))

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
            playlist.append({'name' : channels[channel]['name'], 'url' : base_url + '/play/' + quote(channels[channel]['name'].replace('/', 'sleš')) + '.m3u8', 'logo' : channels[channel]['logo']})
    else:
        for channel in channels:
            playlist.append({'name' : channels[channel]['name'], 'url' : base_url + '/play_num/' + str(channels[channel]['channel_number']) + '.m3u8', 'logo' : channels[channel]['logo']})
    TEMPLATE_PATH.append(os.path.join(get_script_path(), 'resources', 'templates'))
    return template('form.tpl', message = message, playlist_url = playlist_url, playlist_tvheadend_url = playlist_tvheadend_url, epg_url = epg_url, playlist = playlist)

def start_server():
    port = int(get_config_value('webserver_port'))
    run(host = '0.0.0.0', port = port)

