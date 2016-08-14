# -*- coding: utf-8 -*-
from irc3.plugins.command import command
import irc3
import aiohttp
import html
import bs4

@irc3.plugin
class UrbanDictionary(object):

    ud_base_url = "http://www.urbandictionary.com/define.php?term={}"
    ud_template = "UD Definition of \x02{q}\x02 ({num} of {total}) \x02\x035|\x03\x02 {def} \x02\x035|\x03\x02 {short}"

    def __init__(self, bot):
        self.bot = bot
        if hasattr(self.bot, 'session'):
            self.session = self.bot.session
        else:
            self.session = self.bot.session = aiohttp.ClientSession(loop=self.bot.loop)

    
    @classmethod
    def reload(cls, old):
        return cls(old.bot)


    @command(permission='view')
    async def ud(self, mask, target, args):
        """Gets the Urban Dictionary definition of a word.

           Options:
             --num=<n>  which definition to fetch [default: 1]

           %%ud <word>... [--num=<n>]
        """
        q = '+'.join(args['<word>'])
        num = int(args['--num']) - 1 if args['--num'] is not None else 0

        r = await self.session.get(self.ud_base_url.format(q))
        text = await r.text()

        try:
            soup = bs4.BeautifulSoup(text, 'html5lib') # try fast path
        except TypeError:
            soup = bs4.BeautifulSoup(text) # fallback to slow path

        defs = soup.findAll(attrs={'class': 'def-panel'})
        numResults = len(defs)

        try:
            definition = defs[num]
        except IndexError:
            return "Invalid number."

        try:
            defId = definition['data-defid']
            shortlink = "http://{}.urbanup.com/{}".format(
                    q.strip('+').replace('+', '-'), defId)
        except KeyError:
            return "Word not found."

        defText = definition.find(attrs={'class':'meaning'}).text.strip()
        defText = html.unescape(defText)

        ## Magic numbers! Or in other words, truncate the definition so the total length
        ## of the say() is such that it can all fit on one line.
        maxLen = 400
        textLen = 17 + len(q) + 23 + 7 + len(shortlink) + 3 + len(defText)
        if textLen > maxLen:
            truncLen = maxLen - (17 + len(q) + 23 + 7 + len(shortlink) + 3)
            while True:
                if defText[truncLen] == " ":
                    break
                else:
                    truncLen = truncLen - 1
                    continue
            defText = defText[:truncLen] + "..."

        kw = { 'q' : q.strip('+').replace('+', '-'),
            'num': num + 1,
            'total': numResults,
            'def': defText,
            'short': shortlink }
        return self.ud_template.format(**kw)

