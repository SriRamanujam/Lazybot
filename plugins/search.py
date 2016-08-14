# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import logging
import urllib
import copy
import html
import json
import aiohttp

GOOGLE_URL = "https://www.googleapis.com/customsearch/v1?q={q}&key={key}&cx={cx}"
SHORTENER_URL = "https://www.googleapis.com/urlshortener/v1/url?key={key}&cx={cx}"
GOOGLE_BASE_URL = "www.google.com/search?q={q}"
GOOGLE_KG_URL = "https://kgsearch.googleapis.com/v1/entities:search?query={q}&key={key}&limit=1&indent=True"
OUTPUT = "\x02Google search result for {query}\x02 \x02\x0312|\x03\x02 {name} · {snippet} \x02\x0312|\x03\x02 {url} \x02\x0312|\x02\x03 More results: {shortUrl}"

@irc3.plugin
class Search(object):
    
    headers = {
        'User-Agent' : 'python-requests/Lazybot',
        'Cache-Control' : 'max-age=0',
        'Pragma' : 'no-cache',
        'Content-Type' : 'application/json'
    }

    def __init__(self, bot):
        self.bot = bot

        # fetch config options
        module = self.__class__.__module__
        self.config = config = bot.config.get(module, {})
        self.log = logging.getLogger(module)
        if not config:
            self.log.error("Unable to initialize!")
            raise ImportError
        try:
            self.session = aiohttp.ClientSession(loop=self.bot.loop,
                    headers=self.headers)
        except ImportError:
            self.session = None
 

    @classmethod
    def reload(cls, old):
        return cls(old.bot)


    async def create_shorturl(self, s_args):
        """
        Uses goo.gl to generate a shortlink for the search query passed in
        as part of s_args.
        """
        payload = {"longUrl": GOOGLE_BASE_URL.format(**s_args)}
        r = await self.session.post(SHORTENER_URL.format(**s_args),
                data=json.dumps(payload))
        j = await r.json()
        return j['id']

    
    def truncate_string(self, s, length):
        """
        Truncates a string to the nearest space preceding the index given.
        """
        if len(s) < length:
            return s
        while s[length] != " ":
            length -= 1
        return s[:length] + "..."


    async def do_google(self, query):
        """
        Actually performs the google search.
        """
        s_args = copy.deepcopy(self.config)
        s_args['q'] = urllib.parse.quote_plus(query)

        # make the request
        r = await self.session.get(GOOGLE_URL.format(**s_args))
        j = await r.json()
        await r.release()

        res = {}
       
        try:
            res['query'] = query
            res['url'] = urllib.parse.unquote_plus(j['items'][0]['link'])
            res['snippet'] = j['items'][0]['snippet'].encode('utf-8')
            res['name'] = html.unescape(j['items'][0]['title'])
            res['shortUrl'] = await self.create_shorturl(s_args)
            res['snippet'] = self.truncate_string(
                    j['items'][0]['snippet'], 150)
        except KeyError:
            return "No results found."

        if res:
            return OUTPUT.format(**res)
        else:
            return "No results found."


    @command(permission='view')
    async def google(self, mask, target, args):
        """Perform google search

           %%google <query>...
        """
        q = ' '.join(args['<query>'])
        ret = self.do_google(q)
        return (await ret)

