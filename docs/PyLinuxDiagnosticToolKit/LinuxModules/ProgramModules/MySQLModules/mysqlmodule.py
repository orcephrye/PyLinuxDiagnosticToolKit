#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.4
# Date: 05/08/15
# Description:


import logging
import re
from genericCmdModule import GenericCmdModule, dummy_func
from PyCustomCollections.CustomDataStructures import IndexedTable
from PyCustomParsers.GenericParsers import BashParser as GIP


log = logging.getLogger('MySQLModule')


class mysqlModule(GenericCmdModule):

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating MySQL Command Module")
        super(mysqlModule, self).__init__(tki=tki)
        self.defaultCmd = 'ifconfig '
        self.defaultKey = "ifconfig%s"
        self.defaultFlags = ""
        self.__NAME__ = 'mysql'
        self.__LABEL__ = "MySQL"
        self.__CONFIGNAME__ = self.__NAME__+"Config.json"
        self.mysqlServerInstalled = None
        self.mysqlReplication = None
        self.log_error = None
        self.general_log_file = None
        self.slowQueryLogfile = None
        self._mysqlVariables = None
        self._mysqlStatus = None
        self._mysqlSummary = None
        self._mysqlProcessList = None
        self._channelObject = None

    def escalateToMySQL(self):
        if not self._channelObject:
            self._getCustomChannel()
        with self._channelObject as cO:
            cO.escalate(escalationCmd='mysql', escalationArgs="", console=True)
        return

    def run(self, *args, **kwargs):
        return self.initCollection(*args, **kwargs)

    def initCollection(self, *args, **kwargs):
        self.isMySQLClientInstalled()
        self.isMySQLServerInstalled()
        self.isMySQLRunning()
        self.getMySQLVariables()
        self.getMySQLStatus()
        self.getReplicationStatus()
        self.getMySQLProcessList()
        if 'wait' in kwargs:
            return self.tki.waitForIdle(timeout=kwargs.get('wait', 60))
        return None

    def isMySQLClientInstalled(self, *args, **kwargs):
        def _mysqlClientInstalledParser(results=None, *args, **kwargs):
            if '/mysql' in results:
                return results.strip()
            return False
        return self.simpleExecute(command={'whichMysql': 'which mysql'},
                                  postparser=_mysqlClientInstalledParser, **kwargs)

    def isMySQLServerInstalled(self, *args, **kwargs):
        def _isMySQLServerInstalled(results=None, *args, **kwargs):
            if '/mysqld' in results:
                self.mysqlServerInstalled = True
            else:
                self.mysqlServerInstalled = False
            return self.mysqlServerInstalled
        return self.simpleExecute(command={'whichMySQLd': 'which mysqld'}, postparser=_isMySQLServerInstalled, **kwargs)

    def injectMySQL(self, sql=None, **kwargs):
        if not self._channelObject:
            self.escalateToMySQL()
        return self.simpleExecute(command=sql, labelReq=self.__LABEL__, noParsing=True, **kwargs)

    def getReplicationStatus(self, rerun=False, **kwargs):

        requirements = [{'running': self.isMySQLRunning}, {'mysqlCmd': self.isMySQLClientInstalled}]

        return self.simpleExecute(command="%s -e 'show slave status\G'", commandKey='mysqlRep',
                                  preparser=mysqlModule._MySQLStatusPreParser, postparser=self._parseReplication,
                                  requirements=requirements, rerun=rerun, **kwargs)

    def getMySQLVariables(self, rerun=False, wait=0, **kwargs):

        def _mysqlVarPostParser(results, *args, **kwargs):
            self._mysqlVariables = IndexedTable([[item for item in line.split()] for line in results.splitlines()],
                                                columns={'Name': 0, 'Value': 1})
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
            self._mysqlStatus = IndexedTable(columns={'Name': 0, 'Value': 1})
        if self._mysqlSummary is None or rerun:
            self._mysqlSummary = IndexedTable(columns={'Name': 0, 'Value': 1})
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

        return self.simpleExecute(command="%s -N -e 'show processlist'", commandKey='mysqlProcessListCC',
                                  preparser=mysqlModule._MySQLStatusPreParser, postparser=_ParseProcessList,
                                  requirements=requirements, rerun=rerun, wait=wait, **kwargs)

    def isMySQLRunning(self, *args, **kwargs):
        process = self.getMySQLServerProcess(*args, **kwargs)
        if process is None:
            return None
        elif len(process) >= 1:
            return True
        return False

    def getLogFiles(self, wait=30):
        if not self.isMySQLClientInstalled(wait=wait) and self.isMySQLRunning() is not True:
            return None
        self.slowQueryLogfile = self.getVariable('slow_query_log_file', wait=wait)
        self.log_error = self.getVariable('log_error', wait=wait)
        self.general_log_file = self.getVariable('general_log_file', wait=wait)
        if self.general_log_file is None:
            return None
        return {'Slow': self.slowQueryLogfile, 'Error': self.log_error, 'General': self.general_log_file}

    def getMySQLServerProcess(self, *args, **kwargs):
        return self.tki.modules.ps.findCMD('mysqld', *args, **kwargs)

    def getTopRunningProcess(self, top=10, rerun=False, wait=0, **kwargs):
        try:
            if not self._mysqlProcessList or rerun:
                self.getMySQLProcessList(rerun=rerun, wait=wait, **kwargs)
            if type(self._mysqlProcessList) is not GIP:
                return ""
            processList = self._mysqlProcessList
            processList.sort_by_column('Time', reverse=True, column_type=float)
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
            processList.sort_by_column('Time', reverse=True, column_type=float)
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
        results = getattr(self.tki.modules.ps, 'findCMD', dummy_func)(name=('CMD', 'mysqld'), explicit=True,
                                                                      caseSensitive=False, rerun=rerun,
                                                                      wait=wait, **kwargs)
        if not results:
            return None
        return getattr(self.tki.modules.ps, 'formatLines', dummy_func)(results)

    def getVariable(self, name, AND=False, explicit=True, ignore_case=False, wait=30):
        if not self._mysqlVariables or type(self._mysqlVariables) is not IndexedTable:
            self.getMySQLVariables()
        self.getMySQLVariables(wait=wait)
        if type(self._mysqlVariables) is IndexedTable:
            return self._mysqlVariables.search(name, AND=AND, explicit=explicit, ignore_case=ignore_case)
        return None

    def getStatus(self, name, AND=False, explicit=True, ignore_case=False, wait=30):
        if not self._mysqlStatus:
            self.getMySQLStatus(wait=wait)
        if type(self._mysqlStatus) is IndexedTable:
            return self._mysqlStatus.search(name, AND=AND, explicit=explicit, ignore_case=ignore_case)
        return None

    # Privates
    def _getCustomChannel(self):
        if self._channelObject:
            return self._channelObject
        self._channelObject = self.tki.createCustomChannel(label=self.__LABEL__)
        return self._channelObject

    def _parseReplication(self, results, *args, **kwargs):
        output = {'State': "", 'IO': "", 'SQL': "", 'Behind': ""}
        for line in results.splitlines():
            if len(line) <= 1:
                self.mysqlReplication = False
            if 'Slave_IO_State:' in line:
                output['State'] = line.split(': ')[-1]
            elif 'Slave_IO_Running:' in line:
                output['IO'] = line.split(': ')[-1]
            elif 'Slave_SQL_Running:' in line:
                output['SQL'] = line.split(': ')[-1]
            elif 'Seconds_Behind_Master:' in line:
                output['Behind'] = line.split(': ')[-1]
        if output['State']:
            self.mysqlReplication = output
            return self.mysqlReplication
        else:
            return None

    @staticmethod
    def _MySQLStatusPreParser(*args, **kwargs):
        this = kwargs.get("this")
        if this is None:
            return False
        elif not this.requirementResults:
            return False
        else:
            this.command %= str(this.requirementResults.get('mysqlCmd'))
            return True

    @staticmethod
    def _parseProcessListHelper(column):
        if 'Connect' in column:
            if column.splitlines() > 1:
                return tuple(column.split())
        return column
