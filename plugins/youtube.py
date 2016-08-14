# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import aiohttp
import logging
import re

@irc3.plugin
class Youtube(object):

    ytdata_url = "https://www.googleapis.com/youtube/v3/search"
    ytinfo_url = "https://www.googleapis.com/youtube/v3/videos"

    inline_template = '{title} \x034|\x03 Uploaded by {uploader} \x034|\x03 {views} views \x034|\x03 {length}'
    output_template = '\x02YouTube search result\x02 \x034|\x03 {title} \x034|\x03 https://youtube.com/watch?v={id} \x034|\x03 {views} views \x034|\x03 {length}'
    channel_template = '\x02YouTube search result\x02 \x034|\x03 {title} \x034|\x03 https://youtube.com/channel/{id}'

    headers = {
        'User-Agent' : 'python-requests/Lazybot',
        'Cache-Control' : 'max-age=0',
        'Pragma' : 'no-cache',
        'Content-Type' : 'application/json'
    }

    def __init__(self, bot):
        self.bot = bot

        #fetch config options
        module = self.__class__.__module__
        self.config = config = bot.config.get(module, {})
        self.log = logging.getLogger(module)
        if not config:
            self.log.error("Unable to initialize!")
            raise ImportError

        if hasattr(self.bot, 'session'):
            self.session = self.bot.session
        else:
            self.session = self.bot.session = aiohttp.ClientSession(loop=self.bot.loop)


    @classmethod
    def reload(cls, old):
        return cls(old.bot)


    @irc3.event(r'.* PRIVMSG (?P<target>\S+) '
            r':(?P<msg>.*(?:https?://youtu.be/|https?://(www.)?youtube.com/).*)')
    async def on_yt_link(self, target=None, msg=None, **kw):
        if not msg:
            return

        matches = re.findall(
                "(?:https?:\/\/(?:.*?youtube\.com\/watch\?v=)|(?:youtu\.be\/))(\S+)", msg)

        for match in matches:
            amp_index = match.find('&')
            if amp_index > 0:
                match = match[:amp_index]

            data = await self.get_yt_video_data(match)
            title = data['items'][0]['snippet']['title']
            views = "{:,}".format(int(
                data['items'][0]['statistics']['viewCount']))
            length = data['items'][0]['contentDetails']['duration'][2:].lower()
            uploader = data['items'][0]['snippet']['channelTitle']
            self.bot.privmsg(target, self.inline_template.format(
                title=title, views=views, length=length, uploader=uploader))
        return


    async def get_yt_video_data(self, vidId):
        """Get youtube video data given a video id"""
        data_params = {'part' : 'contentDetails,statistics,snippet',
                       'id' : vidId,
                       'fields': 'items/statistics,items/contentDetails,items/snippet',
                       'key' : self.config['key']}
        
        r = await self.session.get(self.ytinfo_url, params=data_params)
        if not r.status == 200:
            error = (await r.json()).get('error')
            if error:
                error = '{code}: {message}'.format(**error)
            else:
                error = r.status_code
            self.log.error(error)
            return {}
        return await r.json()


    @command(permission='view')
    async def yt(self, mask, target, args):
        """Perform youtube search.

           %%yt <query>...
        """
        q = ' '.join(args['<query>'])
        params = { 'part' : 'snippet',
                   'q' : q,
                   'maxResults' : 1,
                   'key': self.config['key'],
                   'safesearch': 'none'}
        r = await self.session.get(self.ytdata_url, params=params)
        if not r.status == 200:
            error = (await r.json()).get('error')
            if error:
                error = '{code}: {message}'.format(**error)
            else:
                error = r.status_code
            self.log.error(error)
            return "Unable to complete Youtube search."

        items = (await r.json())['items']
        if len(items) == 0:
            return "No results found."

        is_channel = False
        for item in items:
            if item['id']['kind'] == "youtube#video":
                entry = item
                break
            elif item['id']['kind'] == "youtube#channel":
                entry = item
                is_channel = True
                break
        else:
            return "No results found."

        if is_channel:
            return self.channel_template.format(title=entry['snippet']['title'],
                    id=entry['id']['channelId'])

        title = entry['snippet']['title']
        id = entry['id']['videoId']

        vid_data = await self.get_yt_video_data(id)

        views = "{:,}".format(int(
            vid_data['items'][0]['statistics']['viewCount']))
        length = vid_data['items'][0]['contentDetails']['duration'][2:].lower()

        return self.output_template.format(
                title=title, id=id, views=views, length=length)
