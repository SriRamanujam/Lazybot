# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import logging
import aiohttp
import json
from enum import Enum

CHANGELOG_TEMPLATE = "\x02Commit {sha}\x02 \x02\x0315|\x03\x02 {msg} \x02\x0315|\x03\x02 {url}"
ISSUE_TEMPLATE = "{intro} {nick} ({user}) in channel {chan}:\n\n {body}"

class IssueType(Enum):
    bug = 1
    feature = 2

@irc3.plugin
class Github(object):

    def __init__(self, bot):
        self.bot = bot

        #fetch config options
        module = self.__class__.__module__
        self.config = config = bot.config.get(module, {})
        self.log = logging.getLogger(module)
        if not config:
            self.log.error("Unable to initialize!")
            raise ImportError

        self.auth = aiohttp.BasicAuth(self.config['username'],
                password=self.config['token'], encoding='utf-8')

        if hasattr(self.bot, "session"):
            self.session = self.bot.session
        else:
            self.session = self.bot.session = aiohttp.ClientSession(
                    loop=self.bot.loop)


    @classmethod
    def reload(cls, old):
        return cls(old.bot)


    @command(permission='view')
    async def changelog(self, mask, target, args):
        """Get the most recent improvements to the bot!

           %%changelog [<num>]
        """
        try:
            q = int(args['<num>']) - 1
        except ValueError:
            q = 0
        except TypeError:
            q = 0

        if q > 29:
            q = 0

        r = await self.session.get(
                'https://api.github.com/repos/SriRamanujam/Lazybot/commits')
        j = await r.json()
        out = j[q]

        return CHANGELOG_TEMPLATE.format(sha=out['sha'][:7],
                msg=out['commit']['message'], url=out['html_url'])

    async def submit_issue(self, title, user, channel, body, type):
        """
        Submit a Github issue.

        :param str title: Issue title
        :param str user: User who submitted issue.
        :param str channel: Channel where issue was submitted.
        :param str body: Body text of issue.
        :param IssueType type: Issue type as enum
        """
        if (type == IssueType.bug):
            tag = 'bug-report'
            intro = 'Issue reported by'
        elif (type == IssueType.feature):
            tag = 'feature-request'
            intro = 'Feature request from'

        issue_params = {
            'intro': intro,
            'nick': user.nick,
            'user': user,
            'chan': channel,
            'body': body
        }
        f = {
            'title': title,
            'body': ISSUE_TEMPLATE.format(**issue_params),
            'labels': [tag]
        }
        r = await self.session.post(
                'https://api.github.com/repos/SriRamanujam/Lazybot/issues',
                data=json.dumps(f), auth=self.auth)
        s = r.status
        j = await r.json()
        if s != 201:
            self.log.error("Status code {}: {}".format(s, j))
            ret = "Github issue creation failed. Please pass this information along to my owner."
        else:
            url = j['html_url']
            ret = "{}: Github issue created! View it at {}".format(
                    user.nick, url)
        return ret


    @command(permission='view')
    async def featurereq(self, mask, target, args):
        """
        Submit a feature request. Links will be stripped from the text.

        Syntax:
        title : body

        %%featurereq <issue>...
        """
        try:
            q = ' '.join(args['<issue>']).split(':', 1)
            q = [a.strip() for a in q]
            title = q[0]
            body = q[1]
        except KeyError:
            return
        except ValueError:
            return

        return (await self.submit_issue(title, mask, target,
            body, IssueType.feature))


    @command(permission='view')
    async def bugreport(self, mask, target, args):
        """
        Submit a bug report. Links will not be submitted as part of the issue.

        Syntax:
        title : body

        %%bugreport <issue>...
        """
        try:
            q = ' '.join(args['<issue>']).split(':', 1)
            q = [a.strip() for a in q]
            title = q[0]
            body = q[1]
        except KeyError:
            return
        except ValueError:
            return

        return (await self.submit_issue(title, mask, target,
            body, IssueType.bug))


