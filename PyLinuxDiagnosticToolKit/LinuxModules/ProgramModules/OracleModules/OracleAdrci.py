#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.3
# Date: 07/16/15
# Name: OracleAdrci.py
# RSAlertOracle.sh
# A Python interface for working with ADRCI Oracle command. This is used to collect data in the 'new' way instead of the
# old way which is supported still in OracleSystem module.


import logging
import re
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('OracleAdrci')


# noinspection PyUnresolvedReferences
class OracleAdrci(GenericCmdModule):

    adrciCmd = None
    oracleLogDict = None

    def __init__(self, *args, **kwargs):
        log.debug(" === Creating Oracle Adrci Module")
        self.oracleLogDict = {}
        super(OracleAdrci, self).__init__(*args, **kwargs)

    def getAdrciCmd(self, **kwargs):
        self.adrciCmd = {str(key): "" for key in self.oracleUsers}

        def _whichAdrciParser(results, **kwargs):
            if isinstance(results, str):
                return None
            for username, value in results.items():
                if 'no adrci in' not in results and 'bin/adrci' in value:
                    self.adrciCmd[username] = "%s |%s ;echo" % ('%s', value)
            return self.adrciCmd

        if len(self.oracleUsers) == 0:
            raise Exception("Unable to create which ADRCI commands because of a lack of Oracle users on this box.")

        cmdKwargs = [self.buildKwargs(command="which adrci", commandKey=str(username), username=str(username))
                     for username in self.oracleUsers]

        if len(cmdKwargs) == 1:
            cmdKwargs = cmdKwargs.pop()
            cmdKwargs.update({'postparser': _whichAdrciParser, 'commandKey': 'whichAdrciCmds'})
            cmdKwargs.update(kwargs)
            return self.simpleExecute(**cmdKwargs)
        elif len(cmdKwargs) > 1:
            return self.simpleExecute(cmdKwargs, commandKey='whichAdrciCmds', postparser=_whichAdrciParser, **kwargs)

    def runADRCICmd(self, adrciCmd, oracleuser, **kwargs):
        adrciCmdDict = self.getAdrciCmd(wait=180)
        if oracleuser not in adrciCmdDict:
            return False
        if not adrciCmdDict[oracleuser]:
            return False

        if 'dbname' not in kwargs:
            kwargs['dbname'] = self.getDefaultSid(oracleuser)

        command = adrciCmdDict[oracleuser] % f'echo -e "{adrciCmd} \nexit"'
        kwargs = self.parsePost(OracleAdrci._adrciPostParser, **kwargs)

        if 'oraclehome' not in kwargs:
            kwargs['oraclehome'] = self.getHome(oracleuser,
                                                data=self.allTheOracleInfo if self.allTheOracleInfo else self._psInfo)

        return self.simpleExecute(**self.buildKwargs(command=command, username=oracleuser, **kwargs))

    def getSIDsInfo(self, oracleuser, **kwargs):

        def _parseSIDs(results, **kwargs):
            return [line.strip().split('/')[-1] for line in results.splitlines()
                    if 'diag/rdbms' in line or 'diag/asm' in line]

        kwargs = self.parsePost(_parseSIDs, **kwargs)

        return self.runADRCICmd('show homes', oracleuser, commandKey='getSidsADRCIshowhomes_%s' % oracleuser, **kwargs)

    def getLogNames(self, oracleuser, **kwargs):

        command = 'show tracefile %.log'
        kwargs['commandKey'] = 'showtracefile_%s' % oracleuser
        oraclebase = kwargs.get('oraclebase', self.getBase(sid=None, username=oracleuser))

        def _parseLogNames(results, **kwargs):
            this = kwargs.get('this')
            results = [oraclebase + "/" + i.strip() for i in results.splitlines()
                        if 'diag/rdbms' in i and 'sbtio' not in i and 'dummy' not in i and '_copy' not in i]
            try:
                OracleUserName = this.commandKey.split('_')[-1]
                self.oracleLogDict[OracleUserName] = results
            except:
                pass
            return results

        kwargs = self.parsePost(_parseLogNames, **kwargs)

        return self.runADRCICmd(command, oracleuser, **kwargs)

    @staticmethod
    def _adrciPostParser(results, *args, **kwargs):
        if not results:
            return False
        if 'adrci>' not in results:
            return False
        output = re.search('adrci>(.+)adrci>', results, flags=re.DOTALL)
        if not output:
            return False
        output = output.group()
        if not output:
            return False
        return output.replace('adrci>', '').strip()
