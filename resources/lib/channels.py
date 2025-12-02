# -*- coding: utf-8 -*-
import sys
import json
import time

from resources.lib.api import call_api
from resources.lib.session import load_session
from resources.lib.utils import load_json_data, save_json_data, display_message, get_config_value

def get_channels():
    md_channels = [{'name' : 'Oneplay Sport 1', 'count' : 8}, {'name' : 'Oneplay Sport 2', 'count' : 8}, {'name' : 'Oneplay Sport 3', 'count' : 4}, {'name' : 'Oneplay Sport 4', 'count' : 4}]
    channels = {}
    token = load_session()

    data = call_api(url = 'https://http.cms.jyxo.cz/api/v1.6/user.profiles.display', data = None, token = token)
    if 'err' in data or 'availableProfiles' not in data or 'profiles' not in data['availableProfiles']:
        display_message('Problém při načtení profilů')
        sys.exit()
    profileId = None
    if get_config_value('profile') is not None and len(get_config_value('profile')) > 0:
        for profile in data['availableProfiles']['profiles']:
            if profile['profile']['name'] == get_config_value('profile'):
                profileId = profile['profile']['id']
    for profile in data['availableProfiles']['profiles']:
        if profileId is None:
            profileId = profile['profile']['id']

    post = {"payload":{"profileId":str(profileId)}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v1.6/epg.channels.display', data = post, token = token)
    if 'err' in data or 'channelList' not in data:
        display_message('Problém při načtení kanálů')
        sys.exit()
    for channel in data['channelList']:
        if 'upsell' not in channel or channel['upsell'] == False:
            image = None
            imagesq = None
            if len(channel['logo']) > 1:
                if image is None:  
                    image = channel['logo'].replace('{WIDTH}', '480').replace('{HEIGHT}', '320')
                if imagesq is None:  
                    imagesq = channel['logo'].replace('{WIDTH}', '256').replace('{HEIGHT}', '256')
            else:
                image = None
                imagesq = None
            if 'flags' in channel and 'adult' in channel['flags']:
                adult = True
            else:
                adult = False
            channels.update({channel['id'] : {'channel_number' : int(channel['order']), 'oneplay_number' : int(channel['order']), 'name' : channel['name'], 'id' : channel['id'], 'logo' : image, 'logosq' : imagesq, 'adult' : adult , 'visible' : True}})
    channel_number = 1000
    for md_channel in md_channels:
        for channel in list(channels):
            if channels[channel]['name'] == md_channel['name']:
                for num in range(1, md_channel['count'] + 1):
                    channels.update({channel + '~' + str(num) : {'channel_number' : channel_number, 'oneplay_number' : channel_number, 'name' : md_channel['name'] + ' MD ' + str(num), 'id' :channel + '~' + str(num), 'logo' : channels[channel]['logo'], 'logosq' : channels[channel]['logosq'], 'adult' : channels[channel]['adult'] , 'visible' : True}})        
                    channel_number = channel_number + 1
    return channels

def load_channels(reset = False):
    channels = {}
    if reset == True:
        channels = get_channels()
        save_channels(channels)
        return channels
    data = load_json_data({'filename' : 'channels.txt', 'description' : 'kanálů'})
    if data is not None:
        data = json.loads(data)
        if 'channels' in data and data['channels'] is not None and len(data['channels']) > 0:
            valid_to = int(data['valid_to'])
            channels_data = data['channels']
            for channel in channels_data:
                channels.update({channel : channels_data[channel]})
        else:
            channels = get_channels()
            save_channels(channels)
        if not valid_to or valid_to == -1 or valid_to < int(time.time()):
            channels = get_channels()
            save_channels(channels)
    else:
        channels = get_channels()
        save_channels(channels)
    return channels

def save_channels(channels):
    valid_to = int(time.time()) + 60*60*24
    data = json.dumps({'channels' : channels, 'valid_to' : valid_to})
    save_json_data({'filename' : 'channels.txt', 'description' : 'kanálů'}, data)
