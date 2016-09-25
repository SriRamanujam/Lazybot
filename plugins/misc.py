import irc3
from irc3.plugins.command import command
import logging
import aiohttp
import json
import random
import bs4

@irc3.plugin
class Misc(object):

    def __init__(self, bot):
        self.bot = bot
        module = self.__class__.__module__
        self.log = logging.getLogger(module)

        if hasattr(self.bot, 'session'):
            self.session = self.bot.session
        else:
            self.session = self.bot.session = aiohttp.ClientSession(loop=self.bot.loop)


    @command(permission='view')
    async def horoscope(self, mask, target, args):
        """
        Get your horoscope! Let out the inner 13-year-old-girl inside.

        %%horoscope <sign>
        """
        q = args['<sign>'].lower()
        url = "http://littleastro.com"
        map = {
            'aries' : 'slide0',
            'taurus' : 'slide1',
            'gemini' : 'slide2',
            'cancer' : 'slide3',
            'leo' : 'slide4',
            'virgo' : 'slide5',
            'libra' : 'slide6',
            'scorpio' : 'slide7',
            'sagittarius' : 'slide8',
            'capricorn' : 'slide9',
            'aquarius' : 'slide10',
            'pisces' : 'slide11',
        }
        r = await self.session.get(url)
        t = await r.text()

        b = bs4.BeautifulSoup(t, "lxml")
        if q in map.keys():
            return b.find('li', attrs={'id': map[q]}).p.text
        else:
            return "Horoscope not available."
    

    @command(permission='view')
    async def doge(self, mask, target, args):
        """
        Get the price of dogecoin in your local currency. Defaults to USD #murica

        %%doge [<currency>]
        """
        q = args['<currency>'].lower() if args['<currency>'] else "usd"
        url = "https://api.cryptonator.com/api/ticker/doge-{}".format(q)

        r = await self.session.get(url)
        j = await r.json()

        if j["success"] == True:
            return "1 DOGE is {} {}".format(j['ticker']['price'], q.upper())
        else:
            return "No results found."


    @command(permission='view')
    async def btc(self, mask, target, args):
        """
        Get the price of BTC in your local currency. Defaults to USD #murica

        %%btc [<currency>]
        """
        q = args['<currency>'].upper() if args['<currency>'] else "USD"
        url = "https://api.coinbase.com/v2/prices/BTC-{}/spot".format(q)

        h = { 'CB-VERSION' : '2016-08-20' }
        r = await self.session.get(url, headers=h)
        j = await r.json()

        if 'data' in j.keys():
            return "1 BTC is {} {}".format(j['data']['amount'], q)
        else:
            print(j)
            return "No results found."


    @command(permission='view')
    def eightball(self, mask, target, args):
        """
        Shake the magic 8 ball, and ~reveal your future~

        %%eightball <question>...
        """
        responses = [
            "It is certain",
            "It is decidedly so",
            "Without a doubt",
            "Yes definitely",
            "You may rely on it",
            "As I see it, yes",
            "Most likely",
            "Outlook good",
            "Yes",
            "Signs point to yes",
            "Reply hazy try again",
            "Ask again later",
            "Better not tell you now",
            "Cannot predict now",
            "Concentrate and ask again",
            "Don't count on it",
            "My reply is no",
            "My sources say no",
            "Outlook not so good",
            "Very doubtful"
        ]
        return "{}: {}".format(mask.nick, random.choice(responses))


