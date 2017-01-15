# -*- coding: utf-8 -*-
import concurrent.futures
import logging
import asyncio
import re
import time

import irc3
from irc3.plugins.command import command

import aiohttp
import praw
from bidict import bidict

@irc3.plugin
class Reddit(object):

    user_agent = "Claire:v4 (by /u/Happy_Man)"
    new_template = "\x02r/{sub}/new\x02 \x037\x02|\x02\x03 {title} by \x02/u/{author}\x02 \x037\x02|\x02\x03 http://redd.it/{id}"
    r_template = "\x02Top post in r/{sub}{time}\x02 \x037\x02|\x02\x03 {title} by \x02/u/{author}\x02 \x037\x02|\x02\x03 {link} \x037\x02|\x02\x03 {shortlink}{nsfw}"
    comment_template = '\x02Comment by /u/{author} \x037|\x03\x02 "{comment}" \x02\x037|\x03\x02 Gilded {gilded} times, {upvotes} upvotes'
    link_template = "\x02r/{sub}\x02 \x037\x02|\x02\x03 {title} - {upvotes} votes \x037\x02|\x02\x03 {num_comments} comments{nsfw}"
    link_regex = re.compile("(?P<link>https?://(?:redd\.it/|w{3}?\.reddit.com/r/\w+/comments/)(?P<link_id>\w+)(?:/\w+/(?P<comment_id>\w+))?)")
    durations = {'hour' : 'in the past hour',
                'day'  : ' in the past day',
                'week' : ' in the past week',
                'month': ' in the past month',
                'year' : ' in the past year',
                'all'  : ' of all time'}
    headers = {}
    chan_map = {} # multireddit => list of channels (could be more than one, you never know)
    generator_map = bidict() # multireddit <=> generator
    sub_map = {} # subreddit => list of multireddits it's in
    time_map = {} # multireddit => latest post time



    def __init__(self, bot):
        def add_to_dict(map, key, value):
            if key not in map.keys():
                map[key] = []
            map[key].append(value)

        self.bot = bot
        module = self.__class__.__module__

        self.praw = praw.Reddit(user_agent=self.user_agent, site_name='my_reddit')
        self.log = logging.getLogger(module)

        if hasattr(self.bot, 'session'):
            self.session = self.bot.session
        else:
            self.session = self.bot.session = aiohttp.ClientSession(loop=self.bot.loop)

        loop = self.bot.loop
        loop.slow_callback_duration = 0.01
        self.config = config = bot.config.get(module, {})
        if not config:
            return

        del config['hash']

        if len(config.keys()) > 0:
            workers = len(config.keys()) + 1
            self.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=workers)

            # set up subreddit fetchers
            cur_time = time.time()
            for channel in config.keys():
                multireddit = config[channel]
                add_to_dict(self.chan_map, multireddit, channel)
                self.time_map[multireddit] = cur_time
                for sub in multireddit.split('+'):
                    add_to_dict(self.sub_map, sub, multireddit)
                self.fetch_subreddit(multireddit)


    async def fetch_reddit_json(self, thing_type, thing_id=None, link=None):
        """
        Retrieves a reddit JSON object based on the type and unique ID.

        :param str type: Type (t1, t2, etc.)
        :param str id: ID of reddit object.
        :param str link: Full Reddit link.
        """
        if thing_type == "t3":
            url = "https://www.reddit.com/api/info.json?id={}_{}".format(thing_type, thing_id)
        elif thing_type == "t1":
            url = link + "/.json"

        r = await self.session.get(url, headers=self.headers)
        j = await r.json()

        if thing_type == "t1":
            return j[1]['data']['children'][0]['data']
        elif thing_type == "t3":
            return j['data']['children'][0]['data']


    @irc3.event(r'.* PRIVMSG (?P<target>\S+) '
                r':(?P<msg>.*https?://(redd.it/|.*\.reddit\.com/).*)')
    async def on_reddit_link(self, target=None, msg=None, **kw):
        """
        When a reddit link matching the event regex is sent in the channel,
        will pretty-print the url showing the information about the reddit post.
        """
        if not msg:
            return

        def truncate_string(s, length):
            """
            Truncates a string to the nearest space preceding the index given.
            """
            if len(s) < length:
                return s
            while s[length] != " ":
                length -= 1
            return s[:length] + "..."

        matches = [m.groupdict() for m in self.link_regex.finditer(msg)]
        for match in matches:
            if match['comment_id']:
                c = await self.fetch_reddit_json('t1', link=match['link'])
                self.bot.privmsg(target, self.comment_template.format(
                    author=c['author'],
                    comment=truncate_string(c['body'], 150),
                    gilded=c['gilded'],
                    upvotes=c['ups']))
            else:
                c = await self.fetch_reddit_json('t3', thing_id=match['link_id'])
                nsfw = " \x037\x02|\x02\x03 \x02NSFW\x02" if c['over_18'] else ""
                self.bot.privmsg(target, self.link_template.format(
                    sub=c['subreddit'],
                    title=c['title'],
                    upvotes=c['ups'],
                    num_comments=c['num_comments'],
                    nsfw=nsfw))


    @command(permission='view')
    async def r(self, mask, target, args):
        """Get top reddit post in subreddit

           %%r <subreddit> [(hour|day|week|month|year|all)]
        """
        return await self.reddit(mask, target, args)


    @command(permission='view')
    async def reddit(self, mask, target, args):
        """Get top reddit post in subreddit

           %%reddit <subreddit> [(hour|day|week|month|year|all)]
        """
        def find_time(args):
            """
            I was too lazy to write a lambda
            """
            sorts = ['hour', 'day', 'week', 'month', 'year', 'all']
            for k in sorts:
                if args[k] is True:
                    return k
            return None

        def get_top(j):
            """
            Get the top submission (excluding stickied posts) from a subreddit
            listing.
            """
            try:
                if len(j['data']['children']) < 1:
                    return None
                entry = None
                for post in j['data']['children']:
                    if not post['data']['stickied']:
                        entry = post['data']
                        break
                return entry
            except KeyError:
                return None

        sub = args['<subreddit>']
        timespan = find_time(args)
        if timespan is None:
            url = "https://www.reddit.com/r/{}/.json".format(sub)
        else:
            url = "https://www.reddit.com/r/{}/top/.json?t={}".format(sub, timespan)

        r = await self.session.get(url, headers=self.headers)
        j = await r.json()
        c = get_top(j)
        if c is None:
            return "Subreddit not found or set to private, sorry :("

        kw = {}
        kw['sub'] = c['subreddit']
        kw['title'] = c['title']
        kw['time'] = self.durations[timespan] if timespan else ""
        kw['author'] = c['author']
        kw['link'] = c['url']
        kw['shortlink'] = "http://redd.it/" + c['id']
        kw['nsfw'] = " \x037\x02|\x02\x03 \x02NSFW\x02" if c['over_18'] else ""
        return self.r_template.format(**kw)


    def fetch_post(self, gen):
        """
        Synchronous function that retrieves the newest post from the
        submission_stream generator.

        @returns c The PRAW submission object representing the newest submission
        @param (c, gen) A tuple containing the PRAW result and the multireddit it came from
        """
        while True:
            try:
                c = next(gen)
                last_target_time = self.time_map[self.generator_map.inv[gen]]
                if c.created > last_target_time:
                    self.time_map[self.generator_map.inv[gen]] = c.created
                    break
            except Exception as e:
                self.log.warning('Exception when retrieving reddit post: %s - %s', type(e).__name__, e)
                return (None, self.generator_map.inv[gen])
        return (c, self.generator_map.inv[gen])


    def print_stream_result(self, c, targets):
        """
        Callback function to print a new Reddit submission to all the channels
        subscribed for that subreddit.

        :param dict c: PRAW submission object
        :param list targets: List of channels to output to
        """
        kw = {}
        kw['sub'] = sub = c.subreddit.display_name.lower()
        kw['title'] = c.title
        kw['author'] = c.author.name
        kw['id'] = c.id
        self.log.debug('outputting to ' + str(targets))
        for t in targets: # should always be a list
            self.bot.privmsg('#' + t, self.new_template.format(**kw))


    async def run_stream(self, gen):
        """
        Coroutine to schedule the next new submission read off of the generator.

        :param gen The generator to schedule
        """
        res = await self.bot.loop.run_in_executor(self.executor, self.fetch_post, gen)
        post = res[0]
        if post is not None:
            targets = self.chan_map[self.generator_map.inv[gen]]
            self.print_stream_result(post, targets)

        multi = res[1]
        asyncio.ensure_future(self.run_stream(self.generator_map[multi]))


    def fetch_subreddit(self, subreddit):
        """
        Sets up the submission fetching loop for the subreddit passed in.

        :param subreddit The subreddit to pass in
        :param chan The channel to output results to
        """
        if self is None or subreddit is None:
            return

        sub = self.praw.subreddit(subreddit)
        gen = sub.stream.submissions()
        for _ in range(100):
            next(gen) # discard first 100 submission, we only want new ones
        self.generator_map[subreddit] = gen
        asyncio.ensure_future(self.run_stream(gen))

