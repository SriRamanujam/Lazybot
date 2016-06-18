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

    SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

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
