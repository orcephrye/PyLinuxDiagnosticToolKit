#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Ryan Henrichson

# Version: 0.1
# Date: 1/05/16
# Name: OracleUser.py
# To be used with teh RSAlertOracle.sh automation script
#


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('OracleUser')


class OracleUser(GenericCmdModule):

    id = None
    username = None
    _ORACLE_HOME = None
    _ORACLE_BASE = None
    _defaultSID = None

    def __init__(self, username, allTheOracle, *args, **kwargs):
        log.debug(" === Creating a Oracle User class with the username: %s" % username)
        super(OracleUser, self).__init__(*args, **kwargs)
        self.ato = allTheOracle
        self.id = self.tki.getModules('id')
        self.username = username
        self._ORACLE_HOME = ''
        self._ORACLE_BASE = ''
        self._defaultSID = ''
        self.getOracleUserInfo()

    def __str__(self):
        return self.username

    def getOracleUserInfo(self, **kwargs):

        def _userParser(results, **kwargs):
            if not isinstance(results, str):
                raise Exception('Results where: %s\nThis is the wrong type needs to be string.' % type(results))
            self._ORACLE_BASE, self._ORACLE_HOME, self._defaultSID = results.split('::')
            return results

        command = {'oracleUser_%s_getinfo' % self.username: 'echo "$ORACLE_BASE::$ORACLE_HOME::$ORACLE_SID"'}

        return self.simpleExecute(**self.ato.buildKwargs(command=command, username=self.username,
                                                         postparser=_userParser, **kwargs))

    @property
    def ORACLE_HOME(self):
        if not self._ORACLE_HOME:
            self.getOracleUserInfo(wait=60)
        return self._ORACLE_HOME

    @property
    def ORACLE_BASE(self):
        if not self._ORACLE_BASE:
            self.getOracleUserInfo(wait=60)
        return self._ORACLE_BASE

    @property
    def defaultSID(self):
        if not self._defaultSID:
            self.getOracleUserInfo(wait=60)
        return self._defaultSID
