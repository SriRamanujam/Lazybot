from peewee import *
from .BaseModel import BaseModel
from .MaskModel import Mask

class User(BaseModel):
    maskid = ForeignKeyField(db_column='maskid', null=False, rel_model=Mask, to_field='id')
    userid = PrimaryKeyField(db_column='userid', null=False)

    class Meta:
        db_table = 'User'
