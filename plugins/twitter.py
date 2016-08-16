# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import aiohttp
import logging
import base64
from collections import namedtuple
import re

class OAuth1(namedtuple('OAuth1', ['consumer_key', 'consumer_secret', 'auth_url', 'aio_loop'])):
    """OAuth1 authentication helper.

    :param str consumer_key: Consumer key
    :param str consumer_secret: Consumer secret
    :param str auth_url: Authentication URL
    """

    def __new__(cls, cons_key, cons_secret, auth_url, aio_session=None):
        if auth_url is None:
            raise ValueError('Must pass authentication url')

        if cons_key is None:
            raise ValueError("Must pass consumer key")

        if cons_secret is None:
            raise ValueError("Must pass consumer secret")

        if aio_session is None:
            aio_session = aiohttp.ClientSession()

        return super().__new__(cls, cons_key, cons_secret, auth_url, aio_session)


    @classmethod
    def decode(cls, auth_header, encoding='latin1'):
        pass


@irc3.plugin
class Twitter(object):

    timeline_url = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={}"
    search_url = "https://api.twitter.com/1.1/search/tweets.json"
    tweet_url = "https://api.twitter.com/1.1/statuses/show/{}.json"
    auth_url = "https://api.twitter.com/oauth2/token"

    tw_template = "Most recent tweet by \x02{name}\x02 (\x02@{user}\x02) \x02\x0310|\x03\x02 {text} \x02\x0310|\x03\x02 https://twitter.com/{user}/status/{id} \x02\x0310|\x03\x02 {time}"
    tws_template = "Most relevant tweet for query \x02{q}\x02 by \x02{name}\x02 (\x02@{user}\x02) \x02\x0310|\x03\x02 {text} \x02\x0310|\x03\x02 https://twitter.com/{user}/status/{id} \x02\x0310|\x03\x02 {time}"
    link_template = "Tweet by \x02{name}\x02 (\x02@{user}\x02) \x02\x0310|\x03\x02 {text} \x02\x0310|\x03\x02 {time}"

    def __init__(self, bot, oauth=None):
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

        # prep headers for initialization during tws call
        self.headers = oauth


    async def tw_auth(self, consumer_key, consumer_secret):
        """Perform OAuth1 flow."""
        base64_key = base64.b64encode(str.encode(
            consumer_key + ":" + consumer_secret, 'utf-8'))
        hlib = {}
        hlib['Authorization'] = "Basic " + base64_key.decode('utf-8')
        hlib['Content-Type'] = "application/x-www-form-urlencoded;charset=UTF-8"

        r = await self.session.post(self.auth_url,
                params="grant_type=client_credentials", headers=hlib)
        j = await r.json()

        if r.status != 200:
            return "Bearer "

        if 'token_type' not in j.keys():
            return "Bearer "

        if j['token_type'] != "bearer":
            return "Bearer "

        return "Bearer " + j['access_token']


    def process_tweet(self, j):
        ret = {}
        ret['id'] = j['id']
        ret['text'] = j['text']
        ret['user'] = j['user']['screen_name']
        ret['name'] = j['user']['name']
        ret['time'] = j['created_at']
        return ret


    @classmethod
    def reload(cls, old):
        return cls(old.bot, old.headers)

    @irc3.event(r'.* PRIVMSG (?P<target>\S+) '
                r':(?P<msg>.*https?.*twitter.com.*)')
    async def on_tw_link(self, target=None, msg=None, **kwargs):
        if not msg:
            return

        if self.headers is None:
            auth = await self.tw_auth(self.config['cons_key'], self.config['cons_secret'])
            self.headers = { 'Authorization' : auth }

        matches = re.findall(
                "(?:https?:\/\/(?:w{3}\.)?twitter\.com\/(?:\w+)\/status(?:es)?\/(\d+))", msg)
        for match in matches:
            r = await self.session.get(self.tweet_url.format(match),
                    headers=self.headers)
            j = await r.json()
            print(j)
            kwargs = self.process_tweet(j)
            self.bot.privmsg(target, self.link_template.format(**kwargs))


    @command(permission='view')
    async def tw(self, mask, target, args):
        """Gets the most recent tweet tweeted by a twitter tweeter.

           %%tw <username>...
        """
        if self.headers is None:
            auth = await self.tw_auth(self.config['cons_key'], self.config['cons_secret'])
            self.headers = { 'Authorization' : auth }

        q = args['<username>'][0]
        r = await self.session.get(self.timeline_url.format(q),
                headers=self.headers)
        j = await r.json()
        params = self.process_tweet(j[0])
        return self.tw_template.format(**params)


    @command(permission='view')
    async def tws(self, mask, target, args):
        """Searches Twitter for your query.

           Supports all query operators that you can use on the website.

           %%tws <query>...
        """
        if self.headers is None:
            self.headers = { 'Authorization' : await self.tw_auth(
                self.config['cons_key'], self.config['cons_secret']) }


        q = ' '.join(args['<query>'])
        params = {'q' : q}
        r = await self.session.get(self.search_url,
                params=params, headers=self.headers)

        if r.status != 200:
            return "Invalid query: {}".format(q)

        try:
            j = await r.json()
            status = j['statuses'][0]
        except KeyError:
            return "No tweets found for query {}".format(q)

        kwargs = self.process_tweet(status)
        kwargs['q'] = q
        return self.tws_template.format(**kwargs)

