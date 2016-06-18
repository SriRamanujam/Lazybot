# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3


@irc3.plugin
class Search(object):
    
    headers = {
        'User-Agent' : 'python-requests/Lazybot',
        'Cache-Control' : 'max-age=0',
        'Pragma' : 'no-cache',
    }

    GOOGLE_URL = "https://www.googleapis.com/customsearch/v1"
    SHORTENER_URL = "https://www.googleapis.com/urlshortener/v1/url?key={key}&cx={cx}"
    GOOGLE_BASE_URL = "www.google.com/search?q={q}"
    GOOGLE_KG_URL = "https://kgsearch.googleapis.com/v1/entities:search?query={q}&key={key}&limit=1&indent=True"

    def __init__(self, bot):
        self.bot = bot
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
    def google(self, mask, target, args):
        """Search using google API

           %%google <query>...
        """
        q = ' '.join(args['<query>'])
        return "hello this is buttcheeks mcgee"
