#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2
# Date: 05/08/15
# Description:


import traceback
import logging
import re
from genericCmdModule import GenericCmdModule
from CommandContainers import CommandContainer
from PyCustomCollections.CustomDataStructures import IndexList
from PyCustomParsers.GenericParser import BashParser as GIP


log = logging.getLogger('MySQLModule')


class mysqlModule(GenericCmdModule):

    # __REQUIRES__ = ['system', 'ps']
    __REQUIRE_ROOT__ = False
    __PRIORITY__ = 10
    __NAME__ = "mysql"
    __RESULTS__ = {}
    __COMMAND__ = {'whichMysql': 'which mysql'}
    __CONFIGNAME__ = __NAME__+"Config.json"
    __LABEL__ = "MySQL"
    __UNBOUND = None
    _mysqlCMD = None
    _mysqlRunning = None
    _mysqlServerInstalled = None
    _mysqlReplication = None
    _mysqlVariables = None
    _mysqlStatus = None
    _mysqlSummary = None
    _mysqlProcessList = None
    _slowQueryLogfile = None
    _logError = None
    _logFile = None
    _proc = None
    _channelObject = None
    cmdI = None

    def __init__(self, cmdI, *args, **kwargs):
        log.info("Creating MySQL Command Module")
        super(mysqlModule, self).__init__(cmdI=cmdI)

    def escalateToMySQL(self):
        if not self._channelObject:
            self._getCustomChannel()
        with self._channelObject as cO:
            cO.escalate(escalationCmd='mysql', escalationArgs="", console=True)
        return

    def exeCmd(self):
        log.info("Executing MySQL Module!")
        if not self.cmdI:
            return False
        return self.initCollection()

    def isMySQLClientInstalled(self, *args, **kwargs):
        def _mysqlClientInstalledParser(results=None, *args, **kwargs):
            if '/mysql' in results:
                self.__RESULTS__ = results
                self._mysqlCMD = results
            return results
        return self.simpleExecute(command=self.__COMMAND__, postparser=_mysqlClientInstalledParser, **kwargs)

    def isMySQLServerInstalled(self, *args, **kwargs):
        def _isMySQLServerInstalled(results=None, *args, **kwargs):
            if '/mysqld' in results:
                self._mysqlServerInstalled = True
            else:
                self._mysqlServerInstalled = False
            return self._mysqlServerInstalled
        return self.simpleExecute(command={'whichMySQLd': 'which mysqld'}, postparser=_isMySQLServerInstalled, **kwargs)

    def injectMySQL(self, sql=None, **kwargs):
        if not self._channelObject:
            self.escalateToMySQL()
        return self.simpleExecute(command=sql, labelReq=self.__LABEL__, noParsing=True, **kwargs)

    def getReplicationStatus(self, rerun=False, **kwargs):
        if not self.cmdI:
            return None

        requirements = [{'running': self.isMySQLRunning}, {'mysqlCmd': self.isMySQLClientInstalled}]

        return self.simpleExecute(command="%s -e 'show slave status\G'", commandKey='mysqlRep',
                                  preparser=mysqlModule._MySQLStatusPreParser, postparser=self._parseReplication,
                                  requirements=requirements, rerun=rerun, **kwargs)

    def getMySQLVariables(self, rerun=False, wait=0, **kwargs):
        if not self.cmdI:
            return None
        if self._mysqlVariables is None or rerun:
            self._mysqlVariables = IndexList(columns={'Name': 0, 'Value': 1})

        def _mysqlVarPostParser(results, *args, **kwargs):
            self._mysqlVariables.extend([[item for item in line.split()] for line in results.splitlines()])
            return self._mysqlVariables

        requirements = [{'running': self.isMySQLRunning}, {'mysqlCmd': self.isMySQLClientInstalled}]

        return self.simpleExecute(command={'mysqlVaraibles': "%s -N -B -e 'show global variables'"},
                                  preparser=mysqlModule._MySQLStatusPreParser, postparser=_mysqlVarPostParser,
                                  requirements=requirements, rerun=rerun, wait=wait, **kwargs)

    def getMySQLStatus(self, rerun=False, **kwargs):

        def _parseShowStatus(results, *args, **kwargs):
            if not results:
                return None
            self._mysqlStatus.extend([[item for item in line.split()] for line in results.splitlines()])
            return self._mysqlStatus

        def _parseStatus(results, *args, **kwargs):
            tempList = [[item.strip() for item in line.split(':')] for line in results.splitlines()]
            self._mysqlStatus.extend(tempList)
            return tempList

        def _parseSummary(results, *args, **kwargs):
            mysqlResults = []
            results = results.split(':')
            for item in results:
                temp = item.strip().split(' ')
                if len(temp) > 1:
                    mysqlResults.append(temp[0])
                    mysqlResults.append(' '.join(temp[1:]).strip())
                elif len(temp) == 1:
                    mysqlResults.append(temp.pop())
            tempList = [[mysqlResults[x], mysqlResults[x+1]] for x in range(0, len(mysqlResults), 2)]
            self._mysqlSummary.extend(tempList)
            del results
            del mysqlResults
            return tempList

        requirements = [{'running': self.isMySQLRunning}, {'mysqlCmd': self.isMySQLClientInstalled}]

        if self._mysqlStatus is None or rerun:
            self._mysqlStatus = IndexList(columns={'Name': 0, 'Value': 1})
        if self._mysqlSummary is None or rerun:
            self._mysqlSummary = IndexList(columns={'Name': 0, 'Value': 1})
        self.simpleExecute(command={'mysqlShowStatus': "%s -N -B -e 'show status'"},
                           preparser=mysqlModule._MySQLStatusPreParser, postparser=_parseShowStatus, rerun=rerun,
                           requirements=requirements, **kwargs)
        self.simpleExecute(command={'mysqlStatus': "%s -e 'status' | tail -20 | head -16"},
                           preparser=mysqlModule._MySQLStatusPreParser, postparser=_parseStatus, rerun=rerun,
                           requirements=requirements, **kwargs)
        self.simpleExecute(command={'mysqlSummary': "%s -e 'status' | tail -3 | head -1"},
                           preparser=mysqlModule._MySQLStatusPreParser, postparser=_parseSummary, rerun=rerun,
                           requirements=requirements, **kwargs)
        if self.mysqlStatus.complete and self.mysqlSummary.complete and self.mysqlShowStatus.complete:
            return self._mysqlStatus
        return None

    def getMySQLProcessList(self, rerun=False, wait=0, **kwargs):

        processTemplate = {'Id': 0, 'User': 1, 'Host': 2, 'db': 3, 'Command': 4, 'Time': 5, 'State': 6, 'Info': 7}
        processHeader = ['Id', 'User', 'Host', 'db', 'Command', 'Time', 'State', 'Info']

        def _ParseProcessList(results, *args, **kwargs):
            if not results:
                return None
            processResults = []
            results = re.sub('(^|\n)\W+($|\n)', '', results, flags=re.DOTALL)
            results = re.split('\|(\s+?\n|\n)', results)
            if len(results) < 3:
                return None
            for item in results:
                if not item:
                    continue
                processitem = re.split('\s+\|\s+', item)
                processitem = [' '.join(x.strip('|').strip("'").strip().split()) for x in processitem]
                if processitem:
                    if 'system user' in processitem:
                        processitem.insert(2, "NULL")
                    if len(processitem) == 1:
                        continue
                    if len(processitem) == 10 and processitem[-1] == '':
                        processitem = processitem[:-1]
                    if len(processitem) > 8:
                        processitem = processitem[:8]
                    processResults.append(processitem)
            self._mysqlProcessList = GIP(source=processResults, columns=processTemplate, header=processHeader)
            return self._mysqlProcessList

        requirements = [{'running': self.isMySQLRunning}, {'mysqlCmd': self.isMySQLClientInstalled}]

        return self.simpleExecute(command="%s -N -e 'show processlist'", commandKey='mysqlProcessList',
                                  preparser=mysqlModule._MySQLStatusPreParser, postparser=_ParseProcessList,
                                  requirements=requirements, rerun=rerun, wait=wait, **kwargs)

    def initCollection(self):
        self.isMySQLClientInstalled()
        self.isMySQLServerInstalled()
        self.isMySQLRunning()
        self.getMySQLVariables()
        self.getMySQLStatus()
        self.getReplicationStatus()
        self.getMySQLProcessList()
        return None

    def isMySQLRunning(self, *args, **kwargs):
        process = self.getMySQLServerProcess(*args, **kwargs)
        if process is None:
            return None
        if len(process) >= 1:
            self._mysqlRunning = True
        else:
            self._mysqlRunning = False
        return self._mysqlRunning

    def getLogFiles(self, wait=30):
        if not self._mysqlCMD and self._mysqlRunning is not True:
            return None
        self._slowQueryLogfile = self.getVariable('slow_query_log_file', wait=wait)
        self._logError = self.getVariable('log_error', wait=wait)
        self._logFile = self.getVariable('general_log_file', wait=wait)
        if self._logFile is None:
            return None
        return {'Slow': self._slowQueryLogfile, 'Error': self._logError, 'General': self._logFile}

    def getMySQLServerProcess(self, *args, **kwargs):
        if self._proc is None:
            self._proc = self.cmdI.getModules('ps')
            if type(self._proc) is None:
                return False
        return self._proc.findCMD('mysqld', *args, **kwargs)

    def getTopRunningProcess(self, top=10, rerun=False, wait=0, **kwargs):
        try:
            if not self._mysqlProcessList or rerun:
                self.getMySQLProcessList(rerun=rerun, wait=wait, **kwargs)
            if type(self._mysqlProcessList) is not GIP:
                return ""
            processList = self._mysqlProcessList
            processList.sort(key='Time', reverse=True, keyType=float)
            if len(processList) < top:
                top = len(self._mysqlProcessList)
            return self._mysqlProcessList.formatLines(lines=processList[0:top])
        except Exception as e:
            log.debug("There was a failure. Error message:\n%s" % e)
            return False

    def getLongRunningProcess(self, threshold=300, rerun=False, wait=0, **kwargs):
        try:
            if not self._mysqlProcessList or rerun:
                self.getMySQLProcessList(rerun=rerun, wait=wait, **kwargs)
            if type(self._mysqlProcessList) is not GIP:
                return None
            processList = self._mysqlProcessList
            processList.sort(key='Time', reverse=True, keyType=float)
            for mysqlProcess in processList:
                if 'system user' in mysqlProcess[1]:
                    continue
                elif float(mysqlProcess[5]) >= threshold:
                    return self._mysqlProcessList.formatLines(lines=[mysqlProcess])
        except Exception as e:
            log.debug("There was a failure. Error message:\n%s" % e)
            return ""
        return ""

    def getMySQLProcess(self, rerun=False, wait=60, **kwargs):
        if self._proc is None:
            self._proc = self.cmdI.getModules('ps')
            if type(self._proc) is None:
                return False
        results = self._proc.findCMD(name=('CMD', 'mysqld'), explicit=True, caseSensitive=False, rerun=rerun,
                                     wait=wait, **kwargs)
        if not results:
            return None
        return self._proc.formatLines(results)

    def getVariable(self, name, explicit=True, caseSensitive=False, wait=30):
        if not self._mysqlVariables or type(self._mysqlVariables) is not IndexList:
            self.getMySQLVariables()
        self.getMySQLVariables(wait=wait)
        if type(self._mysqlVariables) is IndexList:
            return self._mysqlVariables.getSearchValues(name, explicit=explicit, caseSensitive=caseSensitive)
        return None

    def getStatus(self, name, explicit=True, caseSensitive=False, wait=30):
        if not self._mysqlStatus:
            self.getMySQLStatus(wait=wait)
        if type(self._mysqlStatus) is IndexList:
            return self._mysqlStatus.getSearchValues(name, explicit=explicit, caseSensitive=caseSensitive)
        return None

    def setBOUND(self, other=True, bound=True):
        if type(other) is bool:
            self.__UNBOUND = other
        else:
            self.__UNBOUND = bound

    # Privates
    def _getCustomChannel(self):
        if self._channelObject:
            return self._channelObject
        self._channelObject = self.cmdI.createCustomChannel(label=self.__LABEL__)
        return self._channelObject

    def _parseReplication(self, results, *args, **kwargs):
        output = {'State': "", 'IO': "", 'SQL': "", 'Behind': ""}
        for line in results.splitlines():
            if len(line) <= 1:
                self._mysqlReplication = False
            if 'Slave_IO_State:' in line:
                output['State'] = line.split(': ')[-1]
            elif 'Slave_IO_Running:' in line:
                output['IO'] = line.split(': ')[-1]
            elif 'Slave_SQL_Running:' in line:
                output['SQL'] = line.split(': ')[-1]
            elif 'Seconds_Behind_Master:' in line:
                output['Behind'] = line.split(': ')[-1]
        if output['State']:
            self._mysqlReplication = output
            return self._mysqlReplication
        else:
            return None

    @staticmethod
    def _MySQLStatusPreParser(*args, **kwargs):
        this = kwargs.get("this")
        # print "\n=== MySQL Status Pre Parser ==="
        if this is None:
            # print "No this obj"
            return False
        elif not this.requirementResults:
            # print "This has not requirementResults attr"
            return False
        else:
            # print "About to append: %s too: %s" % (str(this.requirementResults.get('mysqlCmd')), this.command)
            this.command %= str(this.requirementResults.get('mysqlCmd'))
            return True

    @staticmethod
    def _parseProcessListHelper(column):
        if 'Connect' in column:
            if column.splitlines() > 1:
                return tuple(column.split())
        return column


def getStackTrace():
    """
        This is a useful troubleshooting tool
    :return:
    """
    return traceback.format_exc()