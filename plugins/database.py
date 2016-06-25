# -*- coding: utf-8 -*-
import peewee
from fuzzywuzzy import fuzz
from irc3.plugins.command import command
import sqlite3
import logging
import irc3
from .models import *
import os.path
import os

@irc3.plugin
class Database(object):
    def __init__(self, bot):
        self.bot = bot
        module = self.__class__.__module__
        self.config = config = bot.config.get(module, {})
        self.log = logging.getLogger(module)
        if not config:
            self.log.error("Unable to initialize!")
            raise ImportError

        self._db = db = BaseModel.db
        path = os.path.join(os.getcwd(), config['db_path'])
        print("Now connecting to " + path)
        db.init(path)
        db.connect()
        # remember to add new tables into this array!
        db.create_tables([User,
            Mask,
            Location,
            Lastfm], safe=True)
        bot.db = self


    def set_user(mask):
        pass


    def get_user(mask):
        # first do a full search for mask
        match = User \
                .select() \
                .join(Mask) \
                .where(Mask.mask == mask) \
                .get() # single result from query
        if match:
            # found a match, return
            print(match)
            return match.userid
        else:
            # do a full fuzzy search on nick + host + ident
            pass
