#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the PS command.


import logging
import re
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParsers import BashParser


log = logging.getLogger('psModule')


class psModule(GenericCmdModule, BashParser):
    """
        psModule class. This class inherits both GenericCmdModule and BashParser. It is used to execute the Linux
        command 'ps' on remote machines.
        defaultCmd: /bin/ps
        defaultFlags = -wweo user,pid,%cpu,%mem,vsz,rss,nlwp,tname,stat,comm,args
        _psHeader = ['USER', 'PID', '%CPU', '%MEM', 'VSZ', 'RSS', 'NLWP', 'TTY', 'STAT', 'CMD', 'COMMAND']
            _psHeader is used by the BashParser which then inherits to help construct the IndexedTable.
    """

    _psColumns = {'USER': 0, 'PID': 1, 'CPU': 2, 'MEM': 3, 'VSZ': 4, 'RSS': 5, 'NLWP': 6,
                   'TTY': 7, 'STAT': 8, 'COMMAND': 9, 'CMDLONG': 10}
    _psHeader = ['USER', 'PID', '%CPU', '%MEM', 'VSZ', 'RSS', 'NLWP', 'TTY', 'STAT', 'COMMAND', 'CMDLONG']
    MEM_VSZ = 'VSZ'
    MEM_RSS = 'RSS'
    MEM = 'MEM'

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ps module.")
        super(psModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(columns=self._psColumns, head=1, header=self._psHeader)
        self.defaultCmd = '/bin/ps '
        self.defaultKey = "psawux"
        self.defaultFlags = "-wweo user,pid,%cpu,%mem,vsz,rss,nlwp,tname,stat,comm,args"
        self.__NAME__ = "ps"

    def run(self, flags=None, rerun=True, **kwargs):
        """ Runs the command '/bin/ps -wweo user,pid,%cpu,%mem,vsz,rss,nlwp,tname,stat,comm,args' by default.

        - :param flags: (string) if passed this will not use the postparser '_formatOutput'.
        - :param rerun: (bool) default True
        - :param kwargs: passed directly to 'simpleExecute'
        - :return:
        """

        def _formatOutput(results, *args, **kwargs):
            self.parse(source=results, refreshData=True)
            return self

        command = {flags or self.defaultKey: self.defaultCmd + (flags or self.defaultFlags)}
        if not flags and 'postparser' not in kwargs:
            kwargs['postparser'] = _formatOutput
        return self.simpleExecute(command=command, rerun=rerun, **kwargs)

    def getProcessByPid(self, pid=None, **kwargs):
        """ Returns a process with the same PID.

        - :param pid: (int)
        - :param kwargs: passed directly to 'correlation'
        - :return: IndexedTable
        """

        self.verifyNeedForRun(**kwargs)
        return self.correlation(('PID', str(pid)), **kwargs)

    def searchProcesses(self, search, **kwargs):
        """ Returns processes with the name from the parameter 'name'.

        - :param search: (str) name of process to search for
        - :param kwargs:  passed directly to 'search'
        - :return: list
        """

        self.verifyNeedForRun(**kwargs)
        return self.search(search, **kwargs)

    def findCMD(self, name, **kwargs):
        """ Returns processes with the name from the parameter 'name'.

        - :param name: (str) name of process to search for
        - :param kwargs:  passed directly to 'getCorrelation'
        - :return: list
        """

        self.verifyNeedForRun(**kwargs)
        return self.correlation(('COMMAND', name), **kwargs)

    def searchCommandString(self, name, **kwargs):
        """ Returns processes with the name from the parameter 'name'.

        - :param name: (str) name of process to search for
        - :param kwargs:  passed directly to 'getCorrelation'
        - :return: list
        """

        self.verifyNeedForRun(**kwargs)
        return self.correlation(('CMDLONG', name), **kwargs)

    def getPIDListByName(self, name, explicit=False, ignore_case=False, **kwargs):
        """ Returns processes PIDs that has the 'name' located inside the 'COMMAND' field of
            '/bin/ps -wweo user,pid,%cpu,%mem,vsz,rss,nlwp,tname,stat,comm,args' output.

        - :param name: (str)
        - :param explicit: argument for the 'search_by_column' method
        - :param ignore_case: argument for the 'search_by_column' method
        - :return: list
        """

        self.verifyNeedForRun(**kwargs)
        return self.search_by_column('COMMAND', name, explicit=explicit, ignore_case=ignore_case)['PID']

    def getTopCPU(self, top=10, **kwargs):
        """ Sorts output from '/bin/ps -wweo user,pid,%cpu,%mem,vsz,rss,nlwp,tname,stat,comm,args' using the CPU
            column and provides the top 10.

        - :param top: (int)
        - :return: list
        """

        self.verifyNeedForRun(**kwargs)
        self.sort_by_column('CPU', reverse=True, column_type=float)
        return self[0:top]

    def getTopMem(self, top=10, memType='MEM', **kwargs):
        """ Sorts output from '/bin/ps -wweo user,pid,%cpu,%mem,vsz,rss,nlwp,tname,stat,comm,args' using the MEM,
            MEM_RSS or MEM_VSZ column and provides the top 10.

        - :param top: (int)
        - :param memType: (str) MEM, or RSS, or MEMVSZ
        - :return: list
        """

        self.verifyNeedForRun(**kwargs)
        if memType == self.MEM or memType == self.MEM_RSS or memType == self.MEM_VSZ:
            self.sort_by_column(memType, reverse=True, column_type=float)
            return self[0:top]

    def getRunQue(self, **kwargs):
        """ Searches the 'STAT' column for the status of 'R' and returns a list of processes found if any. It uses
            cached values unless specified with rerun=True

        - :return: list
        """

        self.verifyNeedForRun(**kwargs)
        return self.search_by_column('STAT', 'R', explicit=False)

    def getProcQueue(self, rerun=True):
        """ Utilizes the 'w' module to determine basic load average summary of the machine.

        - :param rerun: (bool) default True
        - :return: str
        """

        def procQueueParser(results=None, *args, **kwargs):
            parseProcQueueRe = re.search('load average: .*?$', results, flags=re.IGNORECASE|re.MULTILINE)
            if parseProcQueueRe:
                self.procQueue = parseProcQueueRe.group().strip()
            return self.procQueue
        return self.tki.modules.w(commandKey='getProcQueue', postparser=procQueueParser, rerun=rerun)
