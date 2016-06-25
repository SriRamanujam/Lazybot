# -*- coding: utf-8 -*-

from peewee import *
from .BaseModel import BaseModel
from .UserModel import User

class Lastfm(BaseModel):
    lastid = TextField(null=False)
    userid = ForeignKeyField(db_column='userid', null=False, rel_model=User, to_field='userid')

    class Meta:
        db_table = 'Lastfm'
