import irc3
from irc3.plugins.command import command
import bs4
import aiohttp
import logging

@irc3.plugin
class WolframAlpha(object):

    wa_base_url = 'http://api.wolframalpha.com/v2/query?input={q}&appid={appid}'
    wa_validate_url = 'http://api.wolframalpha.com/v2/validatequery?input={q}&appid={appid}'
    wa_output = "\x02WolframAlpha result (beta)\x02 \x02\x038|\x03\x02 {q} \x02\x038|\x03\x02 {ans}"

    def __init__(self, bot):
        self.bot = bot
        module = self.__class__.__module__
        self.log = logging.getLogger(module)
        self.config = config = bot.config.get(module, {})

        self.appid = config['appid']

        if hasattr(self.bot, 'session'):
            self.session = self.bot.session
        else:
            self.session = self.bot.session = aiohttp.ClientSession(loop=self.bot.loop)


    @command(permission='view')
    async def wa(self, mask, target, args):
        """
        Search Wolfram|Alpha for the answer to your question

        %%wa <query>...
        """
        q = '+'.join(args['<query>'])
    
        # validate the query first before spending time waiting on a response
        r = await self.session.get(self.wa_validate_url.format(q=q, appid=self.appid)) 
        xml = await r.text()

        val = bs4.BeautifulSoup(xml, features='xml')
        if (val.validatequeryresult.attrs['success'] != 'true'):
            return "WolframAlpha does not understand your query."

        r = await self.session.get(self.wa_base_url.format(q=q, appid=self.appid))
        xml = await r.text()
        
        # parsing
        obj = bs4.BeautifulSoup(xml, features='xml')
        try:
            answer = obj.queryresult.find('pod', attrs={'primary': 'true'}).plaintext.text
            question = obj.queryresult.find('pod', attrs={'title': 'Input interpretation'}).plaintext.text
        except AttributeError:
            self.log.error("Error retrieving wolframalpha pod information")
            answer = "not found"
            question = q.replace('+', ' ')

        return self.wa_output.format(q=question, ans=answer)
