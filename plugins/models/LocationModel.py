# -*- coding: utf-8 -*-

from peewee import *
from .BaseModel import BaseModel
from .UserModel import User

class Location(BaseModel):
    userid = ForeignKeyField(db_column='userid', null=False, rel_model=User, to_field='userid')
    location = TextField(null=False)

    class Meta:
        db_table = 'location'
