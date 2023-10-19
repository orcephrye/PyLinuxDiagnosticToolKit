#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.1
# Date: 01/04/16
# Name: OracleASMCmd.py
# RSAlertOracle.sh
# A Python interface for working with asmcmd Oracle command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParsers import BashParser


log = logging.getLogger('OracleASMCmd')


# noinspection PyUnresolvedReferences
class ASMCmd(GenericCmdModule):

    def __init__(self, *args, **kwargs):
        log.debug(" === Creating ASMCmd Module")
        super(ASMCmd, self).__init__(*args, **kwargs)

    def asmCmd(self, cmd, **kwargs):

        command = f'asmcmd -p {cmd}'
        kwargs['oracleuser'] = 'grid'
        kwargs['dbname'] = kwargs.get('dbname', self.getDefaultSid('grid'))

        return self.simpleExecute(**self.buildKwargs(command=command, username='grid', **kwargs))

    def duasmcmd(self, directory, **kwargs):
        return self.asmCmd(cmd="du %s" % directory, **self.parsePost(ASMCmd._duPostParser, **kwargs))

    @staticmethod
    def _duPostParser(results, *args, **kwargs):
        if not results:
            return None
        lines = [i.strip().split() for i in results.splitlines() if i != '' and 'ASMCMD' not in i]
        if not (len(lines) > 1):
            return None
        return BashParser(source=lines, head=1, header=0)
