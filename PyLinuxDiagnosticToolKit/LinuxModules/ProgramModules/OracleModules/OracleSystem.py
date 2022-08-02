#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.4.0
# Date: 10-23-14
# Name: OracleSystem
# RSAlertOracle.sh
# Find all the Data related to Oracle on a particular box using the 'old' way. The 'new' way is now mostly in
# OracleAdrci except for Listener related alerts which uses lsnrctrl.


import logging
import re
import os


log = logging.getLogger('OracleSystem')


# noinspection PyUnresolvedReferences
class oracleSystem(object):

    __RESULTS__ = {}
    databaseSearch = re.compile(r"(trm($| ))|(dbs.*hc_)")

    def __init__(self, *args, **kwargs):
        log.debug(" === Creating Oracle System Module")
        super(oracleSystem, self).__init__(*args, **kwargs)

    def initializeData(self):
        """
            Gather information via Process module.
        :return:
        """
        # self.processMod = self.tki.getModules('process')
        self.processMod = self.tki.getModules('ps')
        self.lsof = self.tki.getModules('lsof')
        # self.processMod.runPSCommand()

    def getOraclePmon(self, **kwargs):
        if not self.processMod:
            self.processMod = self.tki.getModules('ps')
            # self.processMod = self.tki.getModules('process')
        self.oraclePMonProcesses = self.processMod.findCMD('ora_pmon', explicit=False, **kwargs)
        return self.oraclePMonProcesses

    def databaseAlert(self, errorCode=99999, runBackupCmd=True):
        # self.processMod.runPSCommand(wait=120)
        # if not self.processMod:
        #     self.processMod = self.tki.getModules('ps')
        self.initializeData()
        self.processMod(wait=120)
        self.oraMmonPids = self.processMod.correlation(('CMDLONG', 'ora_mmon'), explicit=False)
        self.oraMmonPids = dict(zip(self.oraMmonPids['PID'], self.oraMmonPids['CMDLONG']))
        log.debug(" === The oraMmonPids before filter are: %s" % self.oraMmonPids)
        # self._adrciFilter()
        log.debug(" === The oraMmonPids after filter are: %s" % self.oraMmonPids)
        if not self.oraMmonPids:
            log.debug(" === The oraMmonPid is empty. This is likely due to the filter. Adrci has found all logs")
            return True
        self.oralsofFiles = {item: self.lsof.getOpenFilesByPID(item, wait=60) for item in self.oraMmonPids.keys()}
        if not (self.oraMmonPids and self.oralsofFiles):
            return False
        self._parseDataInfoAlert(self.databaseSearch, runBackupCmd=runBackupCmd)
        return True

    def _adrciFilter(self):
        def _filterDict(foundSids, value):
            for sid in foundSids:
                if sid in value:
                    return False
            return True

        if not self.oracleInfo:
            return False

        tempMmonPids = {}
        sidList = [self._getPIDName(i) for i in self.oraMmonPids.values()]
        if not sidList:
            return False
        # oracleHomes = [os.path.basename(sidValues['oracleHomes'])
        #                for homeValues in self.oracleInfo.values()
        #                for sidValues in homeValues.values()]
        oracleHomes = self.oracleInfo['Sid']
        if not oracleHomes:
            return False
        foundSids = list(set(sidList).intersection(set(oracleHomes)))
        for key, value in self.oraMmonPids.items():
            if _filterDict(foundSids, value):
                tempMmonPids[key] = value
        self.oraMmonPids = tempMmonPids
        return True

    def listenerAlert(self):
        if not self.processMod:
            self.processMod = self.tki.getModules('ps')
        self.processMod(wait=120)
        self.tnsPids = self.processMod.correlation(('CMDLONG', 'Tns'), explicit=False, ignore_case=False)['PIDS']
        if self.tnsPids and len(self.tnsPids) > 1:
            self.tnsPids = self._filterIndexedTable(self.tnsPids, '_SCAN')
            self.tnsPids = self.tnsPids.search('LISTENER', explicit=False, ignore_case=False)
        if not self.tnsPids:
            return False
        cmdList = self.tnsPids['CMDLONG']
        homes = [os.path.dirname(os.path.dirname(path)) for path in cmdList]
        sids = []
        for x in range(len(self.tnsPids)):
            pos = self.tnsPids[x].index(cmdList[x])
            tempSid = self.tnsPids[x][pos].split()
            if len(tempSid) > 1:
                tempSid = tempSid[1]
                sids.append(tempSid)
            else:
                sids.append(tempSid.pop())
        pidList = zip(self.tnsPids['USER'], sids, homes)
        exportString = "export ORACLE_HOME=%s ;"
        cmdDict = {}
        for item in pidList:
            home = self._findlsnrctl(item[2])
            if not home:
                continue
            cmdString = "%s status %s"
            cmdString %= (home, item[1])
            cmdDict.update({item[1]: exportString % item[2] + cmdString})
        output = {}
        for key, value in cmdDict.items():
            output[key] = self.tki.execute(commands=value, threading=False)
        if not output:
            return False

        self._parseLsnrctl(cmdOutput=output)
        return True

    def getTraceFile(self):
        if not self.oraError.searchDateLog:
            return None
        fileStr = ""
        for item in self.oraError.searchDateLog:
            for string in item:
                if '.trc' in string:
                    if '.trc:' in string or '.trc.' in string:
                        fileStr = string[:-1]
                    else:
                        fileStr = string
                    break
            if fileStr:
                break
        if fileStr:
            if re.search(r':$', fileStr) or re.search(r'\.$', fileStr):
                self.oraTrace = fileStr[:-1]
                return fileStr[:-1]
            self.oraTrace = fileStr
            return fileStr
        return ""

    def getPIDbyName(self, name=None, wait=0, **kwargs):
        if not name:
            return None
        if not self.processMod:
            self.processMod = self.tki.getModules('ps')
        procList = self.processMod(wait=wait, **kwargs)
        if not procList:
            return None
        procName = "ora_mmon_" + name
        return self.processMod.getPIDListByName(name=procName, wait=wait, explicit=True)

    def getoerrInfo(self, errorCode, home=None):
        self._exportHome()
        if self.oerrHome is None and self.oracleInfo is None:
            return False
        elif self.oerrHome is None and self.oracleCmdBase and self.oracleInfo:
            command = {'oerr': '%s/bin/oerr ora %s 2>/dev/null' % (self.oracleCmdBase, errorCode)}
        elif self.oerrHome:
            value = self.oerrHome.values()
            value = set(value)
            if not value:

                return False
            home = value.pop()
            if not re.search('/$', home):
                home = home + "/"
            command = {'oerr': '%sbin/oerr ora %s 2>/dev/null' % (home, errorCode)}
        else:
            return False
        output = self.tki.execute(commands=command, threading=False)
        if output:
            self.oerrInfo = output
        return self.oerrInfo

    # Privates Functions
    def _findlsnrctl(self, home):

        results = self.tki.modules.find(f'{home} -mount -name lsnrctl 2>/dev/null', parseOutput=False, wait=90)
        return results

    def _parseLsnrctl(self, cmdOutput):
        """
            Should only be called by the listenerAlert function
        :param cmdOutput:
        :return: This should be a dict where its values MUST be strings
        """
        lsnrLogDict = {}
        for sid, lsnrctlOut in cmdOutput.items():
            if not lsnrctlOut:
                continue
            lsnrLogDict[sid] = []
            for lsnrLine in lsnrctlOut.splitlines():
                if 'Listener Log File' in lsnrLine:
                    lsnrName = re.sub(r'Listener Log File +', '', lsnrLine)
                    if re.search(r'/alert/.*\.xml$', lsnrLine):
                        lsnrName = re.sub(r'/alert/.*\.xml$', '/trace/' + sid.lower() + '.log', lsnrName)
                    lsnrLogDict[sid].append(lsnrName.strip())

        self.logFiles = lsnrLogDict
        return self.logFiles

    def _exportHome(self):
        value = None
        if self.oerrHome is None and self.oracleInfo is None:
            return False
        elif self.oerrHome is None and self.oracleCmdBase and self.oracleInfo:
            value = {self.oracleCmdBase}
        elif self.oerrHome:
            value = self.oerrHome.values()
            value = set(value)
        if not value:
            return False
        for item in value:
            self.tki.execute(commands={'export': f'export ORACLE_HOME={item}'}, threading=False)
        return

    def _parseDataInfoAlert(self, search, runBackupCmd=True):
        """
            Should only be called by the databaseAlert function
        :param search:
        :param runBackupCmd:
        :return: This should be a dict where its values MUST be a list of strings
        """
        tmpDict = {}
        findDict = {}
        backupDict = {}
        outputDict = {}
        self.oerrHome = {}

        for eachPid, eachValue in self.oralsofFiles.items():
            if not eachValue:
                continue
            tmpDict[eachPid] = []
            findDict[eachPid] = ""
            logName = '/alert_' + oracleSystem._getPIDName(self.oraMmonPids[eachPid]) + '.log'
            for item in eachValue:
                if 'dbs' in item:
                    self.oerrHome.update({eachPid: item.split('dbs')[0]})
                if search.search(item):
                    if 'trm' in item:
                        tmpDict[eachPid].append(os.path.dirname(item) + logName)
                    else:
                        findDict[eachPid] = {oracleSystem._rootPath(item):
                                             oracleSystem._getPIDName(self.oraMmonPids[eachPid]) + '.log'}

        for key, value in tmpDict.items():
            if value:
                outputDict.update({key: value})
        for key, value in findDict.items():
            if key not in outputDict:
                backupDict.update({key: value})
        if backupDict and runBackupCmd:
            outputDict.update(self._backupFindCmd(findDict=backupDict))
        self.logFiles = outputDict
        return outputDict

    def _backupFindCmd(self, findDict):
        outputDict = None
        if oracleSystem._isNotDictEmpty(findDict):
            outputDict = self._findLogFiles(findDict)
        elif oracleSystem._isNotDictEmpty(self.oerrHome):
            for eachPid, values in self.oerrHome.items():
                findDict[eachPid] = {oracleSystem._rootPath(values):
                                     oracleSystem._getPIDName(self.oraMmonPids[eachPid]) + '.log'}
            outputDict = self._findLogFiles(findDict)
        else:
            for eachPid, eachValue in self.oralsofFiles.items():
                findDict[eachPid] = {self.defaultFindBase:
                                     oracleSystem._getPIDName(self.oraMmonPids[eachPid]) + '.log'}
                outputDict = self._findLogFiles(findDict)
        return outputDict

    def _findLogFiles(self, findDict):
        """
            Should only be ran by the '_backupFindCmd' function
        :param findDict:
        :return: This is a dict where its values MUST be a lists of strings
        """
        outputDict = {}
        for eachPid, value in findDict.items():
            for root, filename in value.items():
                if not re.search(r'^/', root):
                    root = "/" + root
                if not re.search(r'^\*', filename):
                    filename = "*" + filename
                if not re.search(r'\*$', filename):
                    filename = filename + "*"
                results = self.tki.modules.find(f'{root} -mount -mtime -3 -name {filename}s 2>/dev/null',
                                                parseOutput=False, wait=90)
                if results:
                    results = results.splitlines()
                    outputDict[eachPid] = list()
                    for item in results:
                        outputDict[eachPid].append(item)
        # log.debug("The outputDict is: %s" % outputDict)
        return outputDict

    @staticmethod
    def _filterIndexedTable(unfiltered, excludeStr):
        tempList = unfiltered.search(excludeStr, explicit=False)
        if tempList:
            for item in tempList:
                unfiltered.remove(item)
        return unfiltered

    @staticmethod
    def _getPIDName(string):
        return string.split('ora_mmon_')[-1]

    @staticmethod
    def _isNotDictEmpty(testDict):
        for key, value in testDict.items():
            if value:
               return True
        return False

    @staticmethod
    def _rootPath(path):
        lineSplit = path.split('/')
        if len(lineSplit) >= 2:
            return lineSplit[1]
        return path
