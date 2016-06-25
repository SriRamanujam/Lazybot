# -*- coding: utf-8 -*-

from peewee import SqliteDatabase

class SqliteFKDatabase(SqliteDatabase):
    def initialize_connection(self, conn):
        self.execute_sql('PRAGMA foreign_keys=ON;')
