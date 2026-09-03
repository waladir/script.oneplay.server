# -*- coding: utf-8 -*-
import sys
import json
import time

from resources.lib.session import Session
from resources.lib.api import API
from resources.lib.profiles import get_profile_id
from resources.lib.utils import display_message, Settings


# SHARED: Oneplay Server, TVheadend
def get_channels():
    md_channels = {
        'Oneplay Sport 1': 8,
        'Oneplay Sport 2': 8,
        'Oneplay Sport 3': 4,
        'Oneplay Sport 4': 4,
    }
    channels = {}
    session = Session()
    api = API()
    data = api.epg_channels_display(profileId=get_profile_id(session), session=session)
    if not data or 'err' in data or data.get('channelList') is None:
        display_message('Problém při načtení kanálů')
        sys.exit()

    for channel in data['channelList']:
        flags = channel.get('flags') or []
        if channel.get('upsell', False) or 'upsell' in flags:
            continue

        channel_id = channel.get('id')
        name = channel.get('name')
        try:
            channel_number = int(channel['order'])
        except (KeyError, TypeError, ValueError):
            continue
        if not channel_id or not name:
            continue

        logo = channel.get('logo') or ''
        has_logo = len(logo) > 1
        image = logo.replace('{WIDTH}', '390').replace('{HEIGHT}', '228') if has_logo else None
        imagesq = logo.replace('{WIDTH}', '256').replace('{HEIGHT}', '256') if has_logo else None
        channels[channel_id] = {
            'channel_number': channel_number,
            'oneplay_number': channel_number,
            'name': name,
            'id': channel_id,
            'logo': image,
            'logosq': imagesq,
            'adult': 'adult' in flags,
            'visible': True,
        }

    channel_number = 1000
    for channel_id, channel in list(channels.items()):
        stream_count = md_channels.get(channel['name'], 0)
        for number in range(1, stream_count + 1):
            md_channel_id = '{}~{}'.format(channel_id, number)
            channels[md_channel_id] = {
                'channel_number': channel_number,
                'oneplay_number': channel_number,
                'name': '{} MD {}'.format(channel['name'], number),
                'id': md_channel_id,
                'logo': channel['logo'],
                'logosq': channel['logosq'],
                'adult': channel['adult'],
                'visible': True,
            }
            channel_number += 1
    return channels


def load_channels(reset=False):
    if reset:
        channels = get_channels()
        save_channels(channels)
        return channels

    settings = Settings()
    raw_data = settings.load_json_data({'filename': 'channels.txt', 'description': 'kanálů'})
    try:
        data = json.loads(raw_data) if raw_data is not None else {}
        channels = data.get('channels') or {}
        valid_to = int(data.get('valid_to', -1))
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        channels = {}
        valid_to = -1

    if not channels or valid_to < int(time.time()):
        channels = get_channels()
        save_channels(channels)
    return channels


def save_channels(channels):
    valid_to = int(time.time()) + 60 * 60 * 24
    data = json.dumps({'channels': channels, 'valid_to': valid_to})
    settings = Settings()
    settings.save_json_data({'filename': 'channels.txt', 'description': 'kanálů'}, data)


def load_diasbled_channels():
    settings = Settings()
    raw_data = settings.load_json_data({'filename': 'disabled_channels.txt', 'description': 'zakázaných kanálů'})
    try:
        data = json.loads(raw_data) if raw_data is not None else {}
        return data.get('disabled_channels') or []
    except (AttributeError, TypeError, json.JSONDecodeError):
        return []


def save_disabled_channels(disabled_channels):
    channels = load_channels()
    for channel_id, channel in channels.items():
        channel['visible'] = channel_id not in disabled_channels
    save_channels(channels)
    data = json.dumps({'disabled_channels': disabled_channels})
    settings = Settings()
    settings.save_json_data({'filename': 'disabled_channels.txt', 'description': 'zakázaných kanálů'}, data)
