# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3


@irc3.plugin
class Rehash(object):
    def __init__(self, bot):
        self.bot = bot
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        except ImportError:
            self.session = None
    

    @command(permission='all_permissions')
    def rehash(self, mask, target, args):
        """Reload module.

           %%rehash <query>...
        """
        self.bot.log.info('%r', args)
        for plugin in args['<query>']:
            self.bot.reload(plugin)
