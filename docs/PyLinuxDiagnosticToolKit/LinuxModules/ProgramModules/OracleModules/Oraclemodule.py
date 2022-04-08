#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Timothy Nodine, Ryan Henrichson

# Version: 2.0
# Date: 10-23-14
# Name: altOracleModule.py
# altOracleModule.py
# Find the Oracle error in the Oracle log and gets the 5 lines before and after it


import logging
from multiprocessing import RLock
from PyMultiTasking import wait_lock
from PyCustomCollections.CustomDataStructures import IndexList
from OracleData import oracleData
from OracleLogs import oracleLogs
from OracleSystem import oracleSystem
from OracleAdrci import OracleAdrci
from OracleASMCmd import ASMCmd
from OracleSQLPlus import OracleSQLPlus
from OracleUserEscalation import OracleEscalation
from OracleUser import OracleUser


# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.DEBUG)
log = logging.getLogger('oracleModule')


class AllTheOracle(oracleData, OracleEscalation, oracleLogs, oracleSystem, OracleAdrci, ASMCmd, OracleSQLPlus):

    def __init__(self, *args, **kwargs):
        log.debug("Initializing AllTheOracle")
        super(AllTheOracle, self).__init__(*args, **kwargs)


class oracleModule(AllTheOracle):

    __REQUIRE_ROOT__ = True
    __PRIORITY__ = 20
    __NAME__ = "oracle"
    __CONFIGNAME__ = __NAME__+".json"

    oracleUsers = []
    _knownUsers = []
    _knownSIDs = None
    _knownHomes = None
    _psInfo = None
    allTheOracleInfo = None
    _LOCK = None

    def __init__(self, *args, **kwargs):
        super(oracleModule, self).__init__(*args, **kwargs)
        self._LOCK = RLock()

    def run(self, *args, **kwargs):
        log.debug("Running oracle commands!")
        self.initializeData()

    def getOracleUser(self, username):
        return OracleUser(username, self, self.tki)

    def setupDefaultUsers(self):

        def pullName(user):
            return user.username

        def userInKnown(userName):
            return userName in list(map(pullName, self._knownUsers))

        def userInDefault(userName):
            return userName in list(map(pullName, self.oracleUsers))

        def pullKnown(name):
            for x in self._knownUsers:
                if name == x.username:
                    return x

        if not userInDefault('oracle'):
            if userInKnown('oracle'):
                self.oracleUsers.append(pullKnown('oracle'))
            else:
                self.oracleUsers.append(self.getOracleUser('oracle'))
        if not userInDefault('grid'):
            if userInKnown('grid'):
                self.oracleUsers.append(pullKnown('grid'))
            else:
                self.oracleUsers.append(self.getOracleUser('grid'))
        return self.oracleUsers

    # noinspection PyTypeChecker
    def getOracleInfo(self, **kwargs):
        with wait_lock(self._LOCK, timeout=kwargs.get('wait', 180) + 1):
            kwargs['wait'] = kwargs.get('wait', 180)
            self.setupDefaultUsers()
            self.getAltADRCIModule()
            if self.allTheOracleInfo:
                return self.allTheOracleInfo
            self._psInfo = self.getPSInfo(**kwargs)
            allTheOracleInfo = IndexList(values=self._psInfo)
            adrciSids = []
            for user in self.knownUsers:
                tmpSid = self.getSIDsInfo(user.username, **kwargs)
                if tmpSid:
                    adrciSids.extend(tmpSid)
            sids = self._psInfo['Sid']
            newSids = set(sids).difference(set(adrciSids))
            for ns in newSids:
                self._knownSIDs.append(ns)
                allTheOracleInfo.append([user.username, ns, user.ORACLE_HOME])
            self.allTheOracleInfo = allTheOracleInfo
            self.getLogNames('oracle')
            self.getLogNames('grid')
            self.tki.waitForIdle(timeout=kwargs.get('wait'))
        return self.allTheOracleInfo

    def collectOracleData(self, **kwargs):
        return self.getOracleInfo(**kwargs)

    def getPSInfo(self, **kwargs):
        command = 'ps -Ao "%U %p %a"| grep _[p]mon_ | while read line; do ' \
                  'instance_name=$(echo $line|awk -F"_pmon_" ' \
                  '\'{printf $2}\'); proc_id=$(echo $line|awk \'{printf $2}\');  ' \
                  'ORACLE_HOME=$(pwdx $proc_id | awk -F": " \'{printf $2}\'| sed \'s/\/dbs//\'); ' \
                  'ORACLE_USER=$(echo $line| awk \'{printf $1}\'); ' \
                  'echo $ORACLE_USER::$instance_name::$ORACLE_HOME; done'
        command = {'oracleInfoResults': command}

        def _postparser(results, **kwargs):
            template = {'User': 0, 'Sid': 1, 'Home': 2}
            if not results:
                return False
            output = IndexList(values=[row.strip().split('::') for row in results.strip().splitlines()],
                               columns=template)
            self._knownUsers = list(map(self.getOracleUser, set([c[0] for c in output])))
            self._knownSIDs = list(set([c[1] for c in output]))
            self._knownHomes = list(set([c[2] for c in output]))
            return output

        return self.simpleExecute(command, postparser=_postparser, **kwargs)

    def getAltSQLPlusModule(self):
        return self

    def getAltADRCIModule(self):
        return self

    def getAsmcmd(self):
        return self

    def getOracleEsculationModule(self):
        return self

    def getUsers(self):
        if not self.knownUsers:
            self.getPSInfo(wait=180)
        return self.knownUsers

    def getBases(self):
        self.getOracleInfo(wait=180)
        bases = []
        for oracleUser in self.knownUsers:
            bases.append(oracleUser.ORACLE_BASE)
        return bases

    def getSids(self):
        self.getOracleInfo(wait=180)
        return self.knownSIDs

    def getHomes(self):
        self.getOracleInfo(wait=180)
        return self.knownHomes

    def getDefaultSid(self, username):
        try:
            for user in self.knownUsers:
                if user.username == username:
                    return user.defaultSID
        except:
            return ""

    def getHome(self, sid, data=None):
        try:
            if data:
                return data.getSearch('Sid', sid)['Home'].pop()
            return self.getOracleInfo(wait=180).getSearch('Sid', sid)['Home'].pop()
        except:
            return ""

    def getUser(self, sid, data=None):
        try:
            if data:
                return data.getSearch('Sid', sid)['User'].pop()
            return self.getOracleInfo(wait=180).getSearch('Sid', sid)['User'].pop()
        except:
            return ""

    def getBase(self, sid=None, username=None):
        self.getOracleInfo(wait=180)
        username = username or self.getUser(sid)
        if not username:
            return ''
        for user in self.knownUsers:
            if username == user.username:
                return user.ORACLE_BASE

    def getLogs(self, username=None):
        self.getOracleInfo(wait=180)
        if username:
            return self.oracleLogDict.get('username')
        return self.oracleLogDict

    def getLog(self, sid):
        self.getOracleInfo(wait=180)
        for username, logs in self.oracleLogDict.items():
            for logItem in logs:
                if sid in logItem or sid.lower() in logItem.lower():
                    return logItem

    @property
    def oracleInfo(self):
        return self.getOracleInfo(wait=300)

    @property
    def knownUsers(self):
        try:
            if self._knownUsers is None:
                self.getPSInfo(wait=60)
            return self._knownUsers
        except:
            return []

    @property
    def knownSIDs(self):
        try:
            if self._knownSIDs is None:
                self.getPSInfo(wait=60)
            return self._knownSIDs
        except:
            return []

    @property
    def knownHomes(self):
        try:
            if self._knownHomes is None:
                self.getPSInfo(wait=60)
            return self._knownHomes
        except:
            return []


def main():
    print("Please use as module")


if __name__ == '__main__':
    main()
