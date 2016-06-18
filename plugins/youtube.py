# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import logging

@irc3.plugin
class Youtube(object):

    ytdata_url = "https://www.googleapis.com/youtube/v3/search"
    ytinfo_url = "https://www.googleapis.com/youtube/v3/videos"

    output_template = '\x02YouTube search result\x02 \x034|\x03 {title} \x034|\x03 https://youtube.com/watch?v={id} \x034|\x03 {views} views \x034|\x03 {length}'

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
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        except ImportError:
            self.session = None


    @classmethod
    def reload(cls, old):
        return cls(old.bot)


    @command(permission='view')
    def yt(self, mask, target, args):
        """Perform youtube search.

           %%yt <query>...
        """
        q = ' '.join(args['<query>'])
        params = { 'part' : 'snippet',
                   'q' : q,
                   'maxResults' : 1,
                   'key': self.config['key'],
                   'safesearch': 'none'}
        r = self.session.get(self.ytdata_url, params=params)
        if not r.status_code == 200:
            error = r.json().get('error')
            if error:
                error = '{code}: {message}'.format(**error)
            else:
                error = r.status_code
            self.log.error(error)
            return "Unable to complete Youtube search."

        items = r.json()['items']
        if len(items) == 0:
            return "No results found."

        for item in items:
            if item['id']['kind'] == "youtube#video":
                entry = item
                break
        else:
            return "No results found."

        title = entry['snippet']['title']
        id = entry['id']['videoId']

        data_params = {'part' : 'contentDetails,statistics',
                       'id' : id,
                       'fields': 'items/statistics,items/contentDetails',
                       'key' : self.config['key']}
        
        print(str(data_params))

        r2 = self.session.get(self.ytinfo_url, params=data_params)
        if not r2.status_code == 200:
            error = r2.json().get('error')
            if error:
                error = '{code}: {message}'.format(**error)
            else:
                error = r2.status_code
            self.log.error(error)
            return "Unable to complete Youtube search. -- r2 "

        views = "{:,}".format(int(
            r2.json()['items'][0]['statistics']['viewCount']))
        length = r2.json()['items'][0]['contentDetails']['duration'][2:].lower()

        return self.output_template.format(
                title=title, id=id, views=views, length=length)
