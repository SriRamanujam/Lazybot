# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import logging
import asyncio
import functools
import time
import praw
import re

@irc3.plugin
class Reddit(object):

    user_agent = "Claire:v4 (by /u/Happy_Man)"
    new_template = "\x02r/{sub}/new\x02 \x037\x02|\x02\x03 {title} by \x02/u/{author}\x02 \x037\x02|\x02\x03 http://redd.it/{id}"
    r_template = "\x02Top post in r/{sub}{time}\x02 \x037\x02|\x02\x03 {title} by \x02/u/{author}\x02 \x037\x02|\x02\x03 {link} \x037\x02|\x02\x03 {shortlink}{nsfw}"
    comment_template = '\x02Comment by /u/{author} \x037|\x03\x02 "{comment}" \x02\x037|\x03\x02 Gilded {gilded} times, {upvotes} upvotes'
    link_template = "\x02r/{sub}\x02 \x037\x02|\x02\x03 {title} - {upvotes} votes \x037\x02|\x02\x03 {num_comments} comments{nsfw}"
    subreddit_generators = {}
    link_regex = re.compile("(?P<link>https?://(?:redd\.it/|w{3}?\.reddit.com/r/\w+/comments/)(?P<link_id>\w+)(?:/\w+/(?P<comment_id>\w+))?)")
    time_map = { 'hour' : 'in the past hour',
                      'day'  : ' in the past day',
                      'week' : ' in the past week',
                      'month': ' in the past month',
                      'year' : ' in the past year',
                      'all'  : ' of all time' }
    headers = { 'User-Agent' : user_agent }


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

        if hasattr(self.bot, 'session'):
            self.session = self.bot.session
        else:
            self.session = self.bot.session = aiohttp.ClientSession(loop=self.bot.loop)

        # set up subreddit fetchers
        loop = self.bot.loop
        print(config)
        for sub in config.keys():
                self.fetch_subreddit(sub)
        return


    async def fetch_reddit_json(self, type, id=None, link=None):
        """
        Retrieves a reddit JSON object based on the type and unique ID.

        :param str type: Type (t1, t2, etc.)
        :param str id: ID of reddit object.
        :param str link: Full Reddit link.
        """
        if type == "t3":
            url = "https://www.reddit.com/api/info.json?id={}_{}".format(type, id)
        elif type == "t1":
            url = link + "/.json"

        r = await self.session.get(url, headers=self.headers)
        j = await r.json()
        
        if type == "t1":
            return j[1]['data']['children'][0]['data']
        elif type == "t3":
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
                c = await self.fetch_reddit_json('t3', id=match['link_id'])
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
        return (await self.reddit(mask, target, args))


    @command(permission='view')
    async def reddit(self, mask, target, args):
        """Get top reddit post in subreddit
        
           %%reddit <subreddit> [(hour|day|week|month|year|all)]
        """
        def find_time(args):
            sorts = ['hour', 'day', 'week', 'month', 'year', 'all']
            for k in sorts:
                if args[k] is True:
                    return k
            return None

        def get_top(j):
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
        time = find_time(args)
        if time is None:
            url = "https://www.reddit.com/r/{}/.json".format(sub)
        else:
            url = "https://www.reddit.com/r/{}/top/.json?t={}".format(sub, time)

        r = await self.session.get(url, headers=self.headers)
        j = await r.json()
        c = get_top(j)
        if c is None:
            return "Subreddit not found or set to private, sorry :("
       
        kw = {}
        kw['sub'] = c['subreddit']
        kw['title'] = c['title']
        kw['time'] = self.time_map[time] if time else ""
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
        asyncio.ensure_future(self.run_stream(self.subreddit_generators[sub]))
        

    async def run_stream(self, gen):
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
        asyncio.ensure_future(self.run_stream(gen))

