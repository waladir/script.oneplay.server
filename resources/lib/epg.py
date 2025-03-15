# -*- coding: utf-8 -*-
import json
import time
from datetime import datetime

from resources.lib.api import call_api
from resources.lib.session import load_session
from resources.lib.channels import load_channels
from resources.lib.utils import replace_by_html_entity, get_config_value, display_message, save_json_data, load_json_data

def get_channel_epg(channel_id, from_ts, to_ts):
    token = load_session()
    epg = {}
    post = {"payload":{"criteria":{"channelSetId":"channel_list.1","viewport":{"channelRange":{"from":0,"to":200},"timeRange":{"from":datetime.fromtimestamp(from_ts-3600).strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',"to":datetime.fromtimestamp(to_ts-3600).strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'},"schema":"EpgViewportAbsolute"}},"requestedOutput":{"channelList":"none","datePicker":False,"channelSets":False}}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/epg.display', data = post, token = token)
    if 'err' not in data:
        for channel in data['schedule']:
            if channel['channelId'] == channel_id:
                for item in channel['items']:
                    startts = int(datetime.fromisoformat(item['startAt']).timestamp())
                    endts = int(datetime.fromisoformat(item['endAt']).timestamp())
                    if item['actions'][0]['params']['contentType'] in ['show','movie']:
                        id = item['actions'][0]['params']['payload']['deeplink']['epgItem']
                    else:
                        id = item['actions'][0]['params']['payload']['contentId']
                    epg_item = {'id' : id, 'title' : item['title'], 'channel_id' : channel_id, 'description' : item['description'], 'startts' : startts, 'endts' : endts, 'cover' : item['image'].replace('{WIDTH}', '480').replace('{HEIGHT}', '320'), 'poster' : item['image'].replace('{WIDTH}', '480').replace('{HEIGHT}', '320')}
                    epg.update({startts : epg_item})
    return epg

def get_day_epg(from_ts, to_ts):
    token = load_session()
    epg = {}
    post = {"payload":{"criteria":{"channelSetId":"channel_list.1","viewport":{"channelRange":{"from":0,"to":200},"timeRange":{"from":datetime.fromtimestamp(from_ts).strftime('%Y-%m-%dT%H:%M:%S') + '.000Z',"to":datetime.fromtimestamp(to_ts).strftime('%Y-%m-%dT%H:%M:%S') + '.000Z'},"schema":"EpgViewportAbsolute"}},"requestedOutput":{"channelList":"none","datePicker":False,"channelSets":False}}}
    data = call_api(url = 'https://http.cms.jyxo.cz/api/v3/epg.display', data = post, token = token)
    if 'err' not in data:
        for channel in data['schedule']:
            for item in channel['items']:
                startts = int(datetime.fromisoformat(item['startAt']).timestamp())
                endts = int(datetime.fromisoformat(item['endAt']).timestamp())
                if item['actions'][0]['params']['contentType'] == 'show':
                    id = item['actions'][0]['params']['payload']['deeplink']['epgItem']
                else:
                    id = item['actions'][0]['params']['payload']['contentId']
                epg_item = {'id' : id, 'title' : item['title'], 'channel_id' : channel['channelId'], 'description' : item['description'], 'startts' : startts, 'endts' : endts, 'cover' : item['image'].replace('{WIDTH}', '480').replace('{HEIGHT}', '320'), 'poster' : item['image'].replace('{WIDTH}', '480').replace('{HEIGHT}', '320')}
                epg.update({channel['channelId'] + str(startts) : epg_item})
    return epg

def get_epg():
    tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple()))/3600)
    channels = load_channels()
    output = ''
    if len(channels) > 0:
        # try:
        output = '<?xml version="1.0" encoding="UTF-8"?>\n'
        output += '<tv generator-info-name="EPG grabber">\n'
        for id in channels:
            logo = channels[id]['logo']
            if logo is None:
                logo = ''
            if get_config_value('odstranit_hd') == 1 or get_config_value('odstranit_hd') == 'true':
                channel_name = channels[id]['name'].replace(' HD', '')
            else:
                channel_name = channels[id]['name']
            output += '    <channel id="' + replace_by_html_entity(channel_name) + '">\n'
            output += '            <display-name lang="cs">' +  replace_by_html_entity(channel_name) + '</display-name>\n'
            output += '            <icon src="' + logo + '" />\n'
            output += '    </channel>\n'
        today_date = datetime.today() 
        today_start_ts = int(time.mktime(datetime(today_date.year, today_date.month, today_date.day) .timetuple()))
        today_end_ts = today_start_ts + 60*60*24 - 1
        for day in range(int(get_config_value('epg_dnu_zpetne')) * -1, int(get_config_value('epg_dnu_dopredu')), 1):
            cnt = 0
            content = ''
            epg = get_day_epg(today_start_ts + day*60*60*24, today_end_ts + day*60*60*24)
            for ts in sorted(epg.keys()):
                epg_item = epg[ts]
                starttime = datetime.fromtimestamp(epg_item['startts']).strftime('%Y%m%d%H%M%S')
                endtime = datetime.fromtimestamp(epg_item['endts']).strftime('%Y%m%d%H%M%S')
                content = content + '    <programme start="' + starttime + ' +0' + str(tz_offset) + '00" stop="' + endtime + ' +0' + str(tz_offset) + '00" channel="' +  replace_by_html_entity(channels[epg_item['channel_id']]['name']) + '">\n'
                content = content + '       <title lang="cs">' +  replace_by_html_entity(epg_item['title']) + '</title>\n'
                if epg_item['description'] != None and len(epg_item['description']) > 0:
                    content = content + '       <desc lang="cs">' +  replace_by_html_entity(epg_item['description']) + '</desc>\n'
                content = content + '       <icon src="' + epg_item['poster'] + '"/>\n'
                content = content + '    </programme>\n'
                cnt = cnt + 1
                if cnt > 20:
                    output += content
                    content = ''
                    cnt = 0
            output += content
        output += '</tv>\n'
        # except Exception:
        #     display_message('Chyba při stahování EPG!')
    return output                                        

def load_epg(reset = False):
    epg = ''
    if reset == True:
        epg = get_epg()
        save_epg(epg)
        return epg
    data = load_json_data({'filename' : 'epg.txt', 'description' : 'EPG'})
    if data is not None:
        data = json.loads(data)
        if 'epg' in data and len(data['epg']) > 0:
            return data['epg']
        else:
            epg = get_epg()
            save_epg(epg)
    else:
        epg = get_epg()
        save_epg(epg)
    return epg

def save_epg(epg):
    data = json.dumps({'epg' : epg})
    save_json_data({'filename' : 'epg.txt', 'description' : 'EPG'}, data)
