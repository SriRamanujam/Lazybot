# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import requests
import logging
import re

@irc3.plugin
class Twitter(object):

    timeline_url = "https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name={}"
    search_url = "https://api.twitter.com/1.1/search/tweets.json"
    tweet_url = "https://api.twitter.com/1.1/statuses/show/{}.json"

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

        self.session = requests.Session()
        if oauth:
            self.auth = oauth
        else:
            from requests_oauthlib import OAuth1
            self.auth = OAuth1(config['cons_key'], 
                    config['cons_secret'])


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
        return cls(old.bot, old.auth)

    @irc3.event(r'.* PRIVMSG (?P<target>\S+) '
                r':(?P<msg>.*https?.*twitter.com.*)')
    def on_tw_link(self, target=None, msg=None, **kwargs):
        if not msg:
            return

        matches = re.findall(
                "(?:https?:\/\/(?:w{3}\.)?twitter\.com\/(?:\w+)\/status(?:es)?\/(\d+))", msg)
        for match in matches:
            r = self.session.get(self.tweet_url.format(match), auth=self.auth)
            kwargs = self.process_tweet(r.json())
            self.bot.privmsg(target, self.link_template.format(**kwargs))


    @command(permission='view')
    def tw(self, mask, target, args):
        """Gets the most recent tweet tweeted by a twitter tweeter.

           %%tw <username>...
        """
        q = args['<username>'][0]
        r = self.session.get(self.timeline_url.format(q), auth=self.auth)
        params = self.process_tweet(r.json()[0])
        return self.tw_template.format(**params)


    @command(permission='view')
    def tws(self, mask, target, args):
        """Searches Twitter for your query.

           Supports all query operators that you can use on the website.

           %%tws <query>...
        """
        q = ' '.join(args['<query>'])
        params = {'q' : q}
        r = self.session.get(self.search_url, params=params, auth=self.auth)

        if r.status_code != requests.codes.ok:
            return "Invalid query: {}".format(q)

        try:
            j = r.json()['statuses'][0]
        except KeyError:
            return "No tweets found for query {}".format(q)

        kwargs = self.process_tweet(j)
        kwargs['q'] = q
        return self.tws_template.format(**kwargs)





        

