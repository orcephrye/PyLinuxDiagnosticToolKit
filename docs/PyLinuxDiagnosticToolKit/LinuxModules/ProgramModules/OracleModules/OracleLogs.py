#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.4
# Date: 10-23-14
# Name: OracleLogs.py
# RSAlertOracle.sh
# Find the Oracle error in the Oracle log and gets the 5 lines before and after it


import logging
from findError import SearchLog as sLog
from collections import OrderedDict  # TODO remove OrderedDict


log = logging.getLogger('OracleLogs')


# noinspection PyUnresolvedReferences
class oracleLogs(object):

    # __NAME__ = 'oracleLogs'

    def __init__(self, *args, **kwargs):
        log.debug(" === Creating Oracle Logs Module")
        self.allLogsTooOld = False
        self.itemTooOld = False
        super(oracleLogs, self).__init__(*args, **kwargs)

    def getOraError(self, errorCode='99999', listenerAlert=False):
        self._getLogs(listenerAlert, errorCode)
        self._getRemoteTimeZone()
        for eachPid, logList in self.logs.items():
            log.debug("The pid is: %s and the logList type is: %s" % (eachPid, type(logList)))
            if type(logList) is not list:
                fileName = self.logFiles[eachPid]
                if not logList:
                    log.debug("The logList is empty or None")
                    continue
                if self._getOraError(item=logList, eachPid=eachPid, errorCode=errorCode, fileName=fileName):
                    break
            else:
                for item in logList:
                    if not item:
                        log.debug("The logList is empty or None")
                        continue
                    if self._getOraError(item=item, eachPid=eachPid, logList=logList, errorCode=errorCode):
                        break
        if self.oraError is None and self.allLogsTooOld and not self.itemTooOld:
            return False
        elif self.oraError is None and self.itemTooOld:
            return True
        return self.oraError

    def getTraceLog(self, traceFile=None, **kwargs):
        if not traceFile:
            traceFile = self.oraTrace
        if not traceFile:
            return ""
        return self.tki.modules.head(traceFile, wait=120, **kwargs)

    def getSearchLog(self):
        if not self.oraError:
            return None
        return self.oraError.searchLog

    def getSearchDateLog(self):
        if not self.oraError:
            return None
        return self.oraError.searchDateLog

    def getSearchItem(self):
        if not self.oraError:
            return None
        return self.oraError.searchItem

    def isSearchItemTooOld(self):
        return self.oraError._isTooOld(self.oraError.searchDate, ageLimit=3)

    # Private
    def _getOraError(self, item, eachPid, errorCode, logList=None, fileName=None):
        if not fileName and logList:
            fileName = self.logFiles[eachPid][logList.index(item)]
        log.debug("The fileName is: %s and the errorCode is: %s" % (fileName, errorCode))
        tempError = sLog(source=item, searchCode=errorCode, ageLimit=3, remoteTz=self.remoteTz)
        if tempError and tempError.searchDict:
            self.oraError = tempError
            self.logFile = fileName
            return True
        elif tempError and tempError.OLD:
            self.allLogsTooOld = True
        elif tempError and tempError.itemOLD:
            self.itemTooOld = True
        return False

    def _getRemoteTimeZone(self):
        os = self.tki.getModules('os')
        self.remoteTz = os.getTimeZone()
        return

    def _getLogs(self, listenerAlert=False, errorCode=""):
        if not self.logFiles:
            if self.oracleLogs:
                self.logFiles = self.oracleDBToLogs
            else:
                return False
        self.logs = OrderedDict()
        if listenerAlert:
            self._getTNSLogsHelper(errorCode)
            log.debug(" The logs are: %s" % self.logs)
        else:
            self._getORALogsHelper(args='-n 15000')

    def _getORALogsHelper(self, args):
        for eachPid, logList in reversed(self.logFiles.items()):
            log.debug("The eachPid is: %s and the logList value is: %s" % (eachPid, logList))
            if type(logList) is list:
                self.logs[eachPid] = []
                for oraLog in logList:
                    self.logs[eachPid].append(self.tki.modules.tail(f'{oraLog} {args}', wait=120))
            else:
                self.logs[eachPid] = self.tki.modules.tail(f'{logList} {args}', wait=120)

    def _getTNSLogsHelper(self, errorCode):
        errorCode = "\\\""+' '.join(errorCode)+"\\\""
        for eachPid, logList in reversed(self.logFiles.items()):
            log.debug("The eachPid is: %s and the logList value is: %s" % (eachPid, logList))
            if type(logList) is list:
                self.logs[eachPid] = []
                for oraLog in logList:
                    command = self._TNSLogCommand % (oraLog, errorCode)
                    self.logs[eachPid].append(self.simpleExecute(command=command, commandKey=oraLog, wait=122))
            else:
                command = self._TNSLogCommand % (logList, errorCode)
                self.logs[eachPid] = self.simpleExecute(command=command, commandKey=logList, wait=122)
