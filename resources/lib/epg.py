# -*- coding: utf-8 -*-
import json
import time
from datetime import datetime

from resources.lib.api import API
from resources.lib.session import Session
from resources.lib.channels import load_channels
from resources.lib.utils import replace_by_html_entity, get_config_value, display_message, Settings

def get_channel_epg(channel_id, from_ts, to_ts):
    epg = get_day_epg(
        from_ts - 2 * 60 * 60,
        to_ts - 60 * 60,
        selected_channel_id=channel_id,
    )
    return {item['startts']: item for item in epg.values()}

# SHARED: Oneplay Server, TVheadend
def get_day_epg(from_ts, to_ts, selected_channel_id=None):
    channels = load_channels()
    epg = {}
    selected_base_id = selected_channel_id.split('~', 1)[0] if selected_channel_id else None
    post = {
        'payload': {
            'criteria': {
                'channelSetId': 'channel_list.1',
                'viewport': {
                    'channelRange': {'from': 0, 'to': 200},
                    'timeRange': {
                        'from': datetime.fromtimestamp(from_ts).strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',
                        'to': datetime.fromtimestamp(to_ts).strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',
                    },
                    'schema': 'EpgViewportAbsolute',
                },
            },
            'requestedOutput': {
                'channelList': 'none',
                'datePicker': False,
                'channelSets': False,
            },
        }
    }
    api = API()
    session = Session()
    response = api.call_api('epg.display', data=post, session=session)
    if response.get('result', {}).get('status') != 'Ok':
        response = api.call_api('epg.display', data=post, session=session)
    if response.get('result', {}).get('status') == 'Ok':
        data = response.get('result', {}).get('data') or {}
        for channel in data.get('schedule') or []:
            channel_id = channel.get('channelId')
            if selected_base_id and channel_id != selected_base_id:
                continue
            if channel_id in channels:
                for item in channel.get('items') or []:
                    actions = item.get('actions') or []
                    if not actions:
                        continue
                    params = actions[0].get('params') or {}
                    payload = params.get('payload') or {}
                    try:
                        startts = int(datetime.fromisoformat(item.get('startAt')).timestamp())
                        endts = int(datetime.fromisoformat(item.get('endAt')).timestamp())
                    except (TypeError, ValueError):
                        continue
                    if params.get('contentType') or payload.get('contentId'):
                        if params.get('contentType') == 'show' and not payload.get('contentId'):
                            content_id = payload.get('deeplink', {}).get('epgItem')
                        else:
                            content_id = payload.get('contentId')
                        if not content_id:
                            continue
                        labels = item.get('labels') or []
                        is_multidimensional = any(
                            label and label.get('name') == 'content.plugin_mapper.collection_detail_plugin_mapper.action.multi_dimension'
                            for label in labels
                        )
                        if is_multidimensional and (not selected_channel_id or '~' in selected_channel_id):
                            if 'Oneplay Sport ' in channels[channel_id]['name']:
                                stream_number = 1
                                md_post = {"payload": {"contentId": content_id}}
                                md_response = api.call_api('page.content.display', data=md_post, session=session)
                                md_data = md_response.get('result', {}).get('data') or {}
                                md_layout = md_data.get('layout') or {}
                                for block in md_layout.get('blocks') or []:
                                    if block.get('schema') == 'TabBlock':
                                        layout_blocks = block.get('layout', {}).get('blocks') or []
                                        carousels = (layout_blocks[0].get('carousels') or []) if layout_blocks else []
                                        tiles = (carousels[0].get('tiles') or []) if carousels else []
                                        for md_item in tiles:
                                                md_payload = md_item.get('action', {}).get('params', {}).get('payload') or {}
                                                md_id = None
                                                if md_payload.get('criteria'):
                                                    md_id = md_payload['criteria'].get('contentId')
                                                if not md_id:
                                                    md_id = md_payload.get('contentId')
                                                if md_id is not None:
                                                    image = (item.get('image') or '').replace('{WIDTH}', '480').replace('{HEIGHT}', '320')
                                                    epg_item = {
                                                        'id': md_id,
                                                        'title': md_item.get('title', ''),
                                                        'channel_id': channel_id + '~' + str(stream_number),
                                                        'description': '',
                                                        'startts': startts,
                                                        'endts': endts,
                                                        'cover': image,
                                                        'poster': image,
                                                    }
                                                    if not selected_channel_id or epg_item['channel_id'] == selected_channel_id:
                                                        epg[channel_id + '~' + str(stream_number) + str(startts)] = epg_item
                                                stream_number = stream_number + 1
                        if not selected_channel_id or selected_channel_id == channel_id:
                            image = (item.get('image') or '').replace('{WIDTH}', '480').replace('{HEIGHT}', '320')
                            epg_item = {
                                'id': content_id,
                                'payload': payload,
                                'title': item.get('title', ''),
                                'channel_id': channel_id,
                                'description': item.get('description') or '',
                                'startts': startts,
                                'endts': endts,
                                'cover': image,
                                'poster': image,
                            }
                            epg[channel_id + str(startts)] = epg_item
    return epg

def get_live_epg():
    channels = load_channels()
    current_ts = int(time.time())
    epg = get_day_epg(current_ts - 2 * 60 * 60, current_ts + 60 * 60)
    channel_epg = {channel_id: {'now': None, 'next': None} for channel_id in channels}
    for epg_item in sorted(epg.values(), key=lambda item: item['startts']):
        channel_id = epg_item['channel_id']
        if channel_id not in channel_epg:
            continue
        start_time = datetime.fromtimestamp(epg_item['startts']).strftime('%H:%M')
        end_time = datetime.fromtimestamp(epg_item['endts']).strftime('%H:%M')
        time_range = f'{start_time} - {end_time}'
        if (epg_item['startts'] <= current_ts < epg_item['endts']
                and channel_epg[channel_id]['now'] is None):
            channel_epg[channel_id]['now'] = {
                'title': epg_item['title'],
                'time': time_range,
                'startts': epg_item['startts'],
                'endts': epg_item['endts'],
                'description': epg_item.get('description', ''),
                'cover': epg_item.get('cover', ''),
            }
        elif epg_item['startts'] > current_ts and channel_epg[channel_id]['next'] is None:
            channel_epg[channel_id]['next'] = {
                'title': epg_item['title'],
                'time': time_range,
            }
    return channel_epg

# SHARED: Oneplay Server, TVheadend
def get_epg():
    timezone_offset = datetime.now().astimezone().strftime('%z')
    channels = load_channels()
    output = []
    if channels:
        try:
            remove_hd = get_config_value('odstranit_hd') in (1, '1', 'true')
            output.append('<?xml version="1.0" encoding="UTF-8"?>\n')
            output.append('<tv generator-info-name="EPG grabber">\n')
            for channel in channels.values():
                logo = channel.get('logo') or ''
                channel_name = channel['name'].replace(' HD', '') if remove_hd else channel['name']
                escaped_name = replace_by_html_entity(channel_name)
                output.append(f'    <channel id="{escaped_name}">\n')
                output.append(f'            <display-name lang="cs">{escaped_name}</display-name>\n')
                output.append(f'            <icon src="{logo}" />\n')
                output.append('    </channel>\n')
            today = datetime.today()
            today_start_ts = int(time.mktime(datetime(today.year, today.month, today.day).timetuple()))
            today_end_ts = today_start_ts + 24 * 60 * 60 - 1
            days_back = int(get_config_value('epg_dnu_zpetne'))
            days_forward = int(get_config_value('epg_dnu_dopredu'))
            for day in range(-days_back, days_forward):
                day_offset = day * 24 * 60 * 60
                epg = get_day_epg(today_start_ts + day_offset, today_end_ts + day_offset)
                for ts in sorted(epg):
                    epg_item = epg[ts]
                    starttime = datetime.fromtimestamp(epg_item['startts']).strftime('%Y%m%d%H%M%S')
                    endtime = datetime.fromtimestamp(epg_item['endts']).strftime('%Y%m%d%H%M%S')
                    if epg_item['channel_id'] in channels:
                        channel_name = channels[epg_item['channel_id']]['name']
                        if remove_hd:
                            channel_name = channel_name.replace(' HD', '')
                        output.append('    <programme start="' + starttime + ' ' + timezone_offset + '" stop="' + endtime + ' ' + timezone_offset + '" channel="' + replace_by_html_entity(channel_name) + '">\n')
                        output.append('       <title lang="cs">' + replace_by_html_entity(epg_item['title']) + '</title>\n')
                        if epg_item['description']:
                            output.append('       <desc lang="cs">' + replace_by_html_entity(epg_item['description']) + '</desc>\n')
                        output.append('       <icon src="' + epg_item['poster'] + '"/>\n')
                        output.append('    </programme>\n')
            output.append('</tv>\n')
        except Exception:
            display_message('Chyba při stahování EPG!')
    return ''.join(output)

def load_epg(reset=False):
    settings = Settings()
    if reset:
        epg = get_epg()
        save_epg(epg)
        return epg

    raw_data = settings.load_json_data({'filename': 'epg.txt', 'description': 'EPG'})
    try:
        data = json.loads(raw_data) if raw_data else {}
        epg = data.get('epg') or ''
    except (AttributeError, TypeError, json.JSONDecodeError):
        epg = ''
    if epg:
        return epg

    epg = get_epg()
    save_epg(epg)
    return epg

def save_epg(epg):
    settings = Settings()
    data = json.dumps({'epg': epg})
    settings.save_json_data({'filename': 'epg.txt', 'description': 'EPG'}, data)
