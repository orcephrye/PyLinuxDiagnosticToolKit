#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.2
# Date: 10/02/15
# Name: OracleSQLPlus.py
# RSAlertOracle.sh
# A Python interface for working with ADRCI Oracle command. This is used to collect data in the 'new' way instead of the
# old way which is supported still in OracleSystem module.


# A requirement for portray
try:
    from LinuxModules.CommandContainers import CommandContainer
except:
    from ldtk import CommandContainer
import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParser import BashParser


log = logging.getLogger('OracleSQLPlus')


# noinspection PyUnresolvedReferences
class OracleSQLPlus(GenericCmdModule):

    def __init__(self, *args, **kwargs):
        log.debug(" === Creating Oracle SQL Plus Module")
        super(OracleSQLPlus, self).__init__(*args, **kwargs)

    def injectSQL(self, sql, **kwargs):
        """
            Requires either dbname or username/oracleuser.
        :param sql: the sql statement to be injected into the SQL PLUS environment.
        :param kwargs: passed directly into simpleExecute method.
        :return: a CommandContainer or the results within
        """
        if 'dbname' not in kwargs:
            kwargs['dbname'] = self.getDefaultSid(kwargs.get('username', kwargs.get('oracleuser', None)))
        if 'commandKey' not in kwargs:
            kwargs['commandKey'] = CommandContainer._parseCommandInput(sql, '') + "_" + kwargs.get('dbname', 'SQL')

        kwargs.update({'postparser': OracleSQLPlus._sqlParser, 'command': sql, 'sqlplus': True})

        if 'oraclehome' not in kwargs:
            kwargs['oraclehome'] = self.getHome(kwargs.get('dbname'))
        if 'oracleuser' not in kwargs:
            kwargs['oracleuser'] = self.getUser(kwargs.get('dbname'))

        return self.simpleExecute(**self.buildKwargs(**kwargs))

    @staticmethod
    def _sqlParser(results, *args, **kwargs):
        # print(f"\n=== SQL Results: \n{results}\n")
        if not results:
            return None
        if 'ORACLE not available' in results:
            return None
        lines = [i.strip().split() for i in results.splitlines()]
        # print(f'lines: {results}')
        if not (len(lines) >= 4):
            return None
        # Unknown why '-2' is part of this split
        # gcp = BashParser(source=lines[2:-2], head=1, header=0)
        gcp = BashParser(source=lines, head=2, header=0)
        return gcp
