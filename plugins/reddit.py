# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import asyncio
import requests
import logging
import functools
import time
import praw
import re

@irc3.plugin
class Reddit(object):

    user_agent = "Claire:v4 (by /u/Happy_Man)"
    new_template = "\x02r/{sub}/new\x02 \x037\x02|\x02\x03 {title} by \x02/u/{author}\x02 \x037\x02|\x02\x03 http://redd.it/{id}"
    r_template = "\x02Top post in r/{sub} {time}\x02 \x037\x02|\x02\x03 {title} by \x02/u/{author}\x02 {link} \x037\x02|\x02\x03 {shortlink}{nsfw}"
    subreddit_generators = {}
    time_map = { 'hour' : 'in the past hour',
                      'day'  : 'in the past day',
                      'week' : 'in the past week',
                      'month': 'in the past month',
                      'year' : 'in the past year',
                      'all'  : 'of all time' }

    def __init__(self, bot):
        self.bot = bot
        module = self.__class__.__module__
        self.config = config = bot.config.get(module, {})
        del config['hash']
        self.log = logging.getLogger(module)
        if not config:
            self.log.error("Unable to initialize!")
            raise ImportError

        self.praw = praw.Reddit(self.user_agent)

        # set up subreddit fetchers
        loop = self.bot.loop
        print(config)
        for sub in config.keys():
                self.fetch_subreddit(sub)
        return


    @command(permission='view')
    def reddit(self, mask, target, args):
        """Get top reddit post in subreddit
        
           %%reddit <subreddit> [(hour|day|week|month|year|all)]
        """
        def find_time(args):
            sorts = ['hour', 'day', 'week', 'month', 'year', 'all']
            for k in sorts:
                if args[k] is True:
                    return k
            return None

        def get_top(sub, time):
            try:
                if time is None:
                    return next(sub.get_top(limit=1))
                else:
                    m = 'get_top_from_' + time
                    mth = getattr(sub, m)
                    return next(mth(limit=1))
            except Exception:
                return None


        sub = args['<subreddit>']
        time = find_time(args)
        sub = self.praw.get_subreddit(args['<subreddit>'])
        c = get_top(sub, time)
        if c is None:
            return "Subreddit not found or set to private, sorry :("
       
        kw = {}
        kw['sub'] = sub.display_name
        kw['title'] = c.title
        kw['time'] = self.time_map[time]
        kw['author'] = c.author.name
        kw['link'] = c.url
        kw['shortlink'] = "http://redd.it/" + c.id
        kw['nsfw'] = " \x037\x02|\x02\x03 \x02NSFW\x02" if c.over_18 else ""
        return self.r_template.format(**kw)
        


    def fetch_post(self, gen):
        """
        Synchronous function that retrieves the newest post from the
        submission_stream generator.

        @returns c The PRAW submission object representing the newest submission
        @param gen The submission_stream generator
        """
        c = next(gen)
        return c


    def print_stream_result(self, future):
        """
        Callback function to print a new Reddit submission to all the channels
        subscribed for that subreddit.

        @param future Future containing the PRAW submission object to be posted.
        """
        c = future.result()
        print(c)
        kw = {}
        kw['sub'] = sub = c.subreddit.display_name
        kw['title'] = c.title
        kw['author'] = c.author.name
        kw['id'] = c.id
        targets = self.config[sub]
        if isinstance(targets, str):
            self.bot.privmsg(targets, self.new_template.format(**kw))
        else:
            for t in targets:
                self.bot.privmsg(t, self.new_template.format(**kw))
        asyncio.async(self.run_stream(self.subreddit_generators[sub]))
        

    @asyncio.coroutine
    def run_stream(self, gen):
        """
        Coroutine to schedule the next new submission read off of the generator.
        
        @param gen The generator to schedule
        """
        fut = self.bot.loop.run_in_executor(None, self.fetch_post, gen)
        fut.add_done_callback(self.print_stream_result)


    def fetch_subreddit(self, subreddit):
        """
        Sets up the submission fetching loop for the subreddit passed in.

        @param subreddit The subreddit to pass in
        """
        if self is None or subreddit is None:
            return

        gen = praw.helpers.submission_stream(
                self.praw, subreddit, limit=1, verbosity=0)
        next(gen) # discard first entry
        self.subreddit_generators[subreddit] = gen
        asyncio.async(self.run_stream(gen))
