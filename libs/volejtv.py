# -*- coding: utf-8 -*-
import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

import json
from datetime import datetime
import time

from libs.utils import get_url

if len(sys.argv) > 1:
    _handle = int(sys.argv[1])

tz_offset = int((time.mktime(datetime.now().timetuple())-time.mktime(datetime.utcnow().timetuple())))

def call_api(url, data = None, method = None):
    addon = xbmcaddon.Addon()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0', 'Accept': 'application/json; charset=utf-8'}    
    if data != None:
        data = urlencode(data)
        data = data.encode('utf-8')
    if method is not None:
        request = Request(url = url , data = data, method = method, headers = headers)
    else:
        request = Request(url = url , data = data, headers = headers)

    if addon.getSetting('log_api_calls') == 'true':
        xbmc.log(str(url))
        xbmc.log(str(data))
    try:
        html = urlopen(request).read()
        if addon.getSetting('log_api_calls') == 'true':
            xbmc.log(str(html))
        if html and len(html) > 0:
            data = json.loads(html)
            return data
        else:
            return []
    except HTTPError as e:
        return { 'err' : e.reason } 
    except URLError as e:
        return { 'err' : e.reason }      

def play_volejtv_live_stream(id):
    from random import randint
    userid = randint(100000000000, 999999999999)
    response = call_api(url = 'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/match/' + str(id) + '?userId=' + str(userid))
    if response['livematch']['video_url'] is not None:
        url = 'https:' + response['livematch']['video_url']
        list_item = xbmcgui.ListItem()
        list_item.setPath(url + '|Referer=https://volej.tv/')    
        list_item.setContentLookup(False)
        xbmcplugin.setResolvedUrl(_handle, True, list_item)
    else:
        xbmcgui.Dialog().notification('Volej.tv', 'Stream není k dispozici', xbmcgui.NOTIFICATION_ERROR, 5000)

def play_volejtv_stream(id):
    addon = xbmcaddon.Addon()
    response = call_api(url = 'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/match/' + str(id))
    if addon.getSetting('volejtv_quality') == 'nízká':
        index = -2
    else:
        index = -1
    url = response['videos'][0]['qualities'][index]['cloud_front_path']
    list_item = xbmcgui.ListItem()
    list_item.setPath(url + '|Referer=https://volej.tv/')    
    list_item.setContentLookup(False)
    xbmcplugin.setResolvedUrl(_handle, True, list_item)

def get_volejtv_live_streams():
    today_date = datetime.today() 
    today_end_ts = int(time.mktime(datetime(today_date.year, today_date.month, today_date.day).timetuple())) + 60*60*24-1
    live_streams = []
    response = call_api(url = 'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/match/by-category-id-paginated/8?page=1&take=20&order=ASC')
    if 'data' in response:
        for item in response['data']:
            event_id = item['id']
            home_team_id = item['home_team_id']
            guest_team_id = item['guest_team_id']
            home_team = ''
            guest_team = ''
            image = ''
            for team in item['teams']:
                if team['id'] == home_team_id:
                    home_team = team['title']
                    if 'match_background_url' in team and team['match_background_url'] is not None and '480' in team['match_background_url']:
                        image = team['match_background_url']['480'] + '|Referer=https://volej.tv/'
                if team['id'] == guest_team_id:
                    guest_team = team['title']
            title = home_team + ' - ' + guest_team + '\n' + '[COLOR=gray]' + item['competition_name'] + '[/COLOR]'
            startts = int(time.mktime(time.strptime(item['match_time'][:-6], '%Y-%m-%dT%H:%M:%S'))) + tz_offset
            if startts < time.mktime(datetime.now().timetuple()):
                print(item)
                live_streams.append({ 'service' : 'volej.tv', 'type' : 'live', 'link' : event_id, 'playable' : 1, 'cas' : datetime.strftime(datetime.fromtimestamp(startts), '%H:%M'), 'startts' : startts, 'endts' : None, 'title' : title, 'image' : image})
            elif startts < today_end_ts:
                print(item)
                live_streams.append({ 'service' : 'volej.tv', 'type' : 'future', 'link' : event_id, 'playable' : 0, 'cas' : datetime.strftime(datetime.fromtimestamp(startts), '%H:%M'), 'startts' : startts, 'endts' : None, 'title' : title, 'image' : image})                
    return live_streams

def list_volejtv_live(label):
    xbmcplugin.setPluginCategory(_handle, label)
    streams = get_volejtv_live_streams()
    for stream in streams:
        if stream['type'] == 'live':
            list_item = xbmcgui.ListItem(label = stream['title'] +  ' (' + stream["cas"] + ')')
            list_item.setInfo('video', {'title' : stream['title']}) 
            list_item.setArt({'icon': stream['image']})
            url = get_url(action='play_volejtv_live_stream', id = stream['link']) 
            list_item.setContentLookup(False)          
            list_item.setProperty('IsPlayable', 'true')        
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        else:
            list_item = xbmcgui.ListItem(label = '[COLOR=gray]' + stream['title'] +  ' (' + stream["cas"] + ')' + '[/COLOR]')
            list_item.setInfo('video', {'title' : stream['title'], 'plot' : stream['title'] + ' (' + stream["cas"] + ')'}) 
            list_item.setArt({'icon': stream['image']})
            url = get_url(action='list_volejtv_live', label = label)  
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
    xbmcplugin.endOfDirectory(_handle)  

def list_volejtv_category(label, category_id, page):
    xbmcplugin.setPluginCategory(_handle, label)
    page = int(page)
    if page == 1:
        response = call_api(url = 'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/category')
        if len(response) > 0: 
            for category in response:
                if 'parent_id' in category and category['parent_id'] == int(category_id):
                    subcategory_id = category['id']
                    name = category['title']
                    name = name[0].upper() + name[1:]
                    list_item = xbmcgui.ListItem(label = name)
                    url = get_url(action='list_volejtv_category', label = ' \ ' + name, category_id = str(subcategory_id), page = 1)  
                    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    if page > 1:
        list_item = xbmcgui.ListItem(label = 'Předchozí strana')
        url = get_url(action='list_volejtv_category', label = label, category_id = str(category_id), page = page - 1)  
        xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    response = call_api(url = 'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/match/by-category-id-paginated/' + str(category_id) + '?page=' + str(page) + '&take=20&order=DESC')
    if 'data' in response:
        for item in response['data']:
            event_id = item['id']
            home_team_id = item['home_team_id']
            guest_team_id = item['guest_team_id']
            home_team = ''
            guest_team = ''
            if item['videos'][0]['description'] is not None:
                description = item['videos'][0]['description']
            else:
                description = ''
            image = ''
            for team in item['teams']:
                if team['id'] == home_team_id:
                    home_team = team['title']
                    if 'match_background_url' in team and team['match_background_url'] is not None and '480' in team['match_background_url']:
                        image = team['match_background_url']['480'] + '|Referer=https://volej.tv/'
                if team['id'] == guest_team_id:
                    guest_team = team['title']
            title = home_team + ' - ' + guest_team
            startts = int(time.mktime(time.strptime(item['match_time'][:-6], '%Y-%m-%dT%H:%M:%S'))) + tz_offset
            list_item = xbmcgui.ListItem(label = title + ' (' + datetime.strftime(datetime.fromtimestamp(startts), '%d.%m.%Y %H:%M') + ')\n' + '[COLOR=gray]' + description + '[/COLOR]')
            list_item.setInfo('video', {'title' : title, 'plot' : title + '\n' + description}) 
            list_item.setArt({'icon': image})
            url = get_url(action='play_volejtv_stream', id = event_id) 
            list_item.setContentLookup(False)          
            list_item.setProperty('IsPlayable', 'true')        
            xbmcplugin.addDirectoryItem(_handle, url, list_item, False)
        if page < response['meta']['pageCount']:
            list_item = xbmcgui.ListItem(label = 'Následující strana')
            url = get_url(action='list_volejtv_category', label = label, category_id = str(category_id), page = page + 1)  
            xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)

def list_volejtv_main(label):
    xbmcplugin.setPluginCategory(_handle, label)

    list_item = xbmcgui.ListItem(label = 'Live a plánované streamy')
    url = get_url(action='list_volejtv_live', label = 'Live a plánované streamy')  
    xbmcplugin.addDirectoryItem(_handle, url, list_item, True)

    response = call_api(url = 'https://api-volejtv-prod.apps.okd4.devopsie.cloud/api/category')
    if len(response) > 0: 
        for category in response:
            if 'parent_id' in category and category['parent_id'] is None:
                category_id = category['id']
                name = category['title']
                name = name[0].upper() + name[1:]
                list_item = xbmcgui.ListItem(label = name)
                url = get_url(action='list_volejtv_category', label = name, category_id = str(category_id), page = 1)  
                xbmcplugin.addDirectoryItem(_handle, url, list_item, True)
    xbmcplugin.endOfDirectory(_handle, cacheToDisc = True)
