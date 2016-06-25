# -*- coding: utf-8 -*-

from peewee import *
from .BaseModel import BaseModel

class Mask(BaseModel):
    mask = TextField(null=False)
    host = TextField(null=False)
    ident = TextField(null=False)
    nick = TextField(null=False)
    user = TextField(null=False)
    id = PrimaryKeyField(null=False)

    class Meta:
        db_table = 'Mask'

