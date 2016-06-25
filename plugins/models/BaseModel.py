# -*- coding: utf-8 -*-

from peewee import *
from .SqliteFKDatabase import SqliteFKDatabase

db = SqliteFKDatabase(None)

class BaseModel(Model):
    class Meta:
        database = db
