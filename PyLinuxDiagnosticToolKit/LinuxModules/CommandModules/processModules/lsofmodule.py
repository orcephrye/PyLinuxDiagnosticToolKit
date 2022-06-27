#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.1.9
# Date: 7/12/16
# Description: This is a module for using the lsof command.

'''
TODO: This module is broken. The SIZE/OFF column can either show size in bits, offset in memory, or nothing.
'''

import logging
import re
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParsers import BashParser


log = logging.getLogger('lsofModule')


class lsofModule(GenericCmdModule, BashParser):
    """
        lsofModule class. This class inherits both GenericCmdModule and BashParser. It is used to execute the Linux
        command 'lsof' on remote machines.
        defaultCmd: lsof
        defaultFlags = -w -S 2
    """

    _lsofStrFormat = '{0:<[0]}{1:<[1]}{2:<[2]}{3:<[3]}{4:<[4]}{5:<[5]}{6:<[6]}{7:<[7]}{8:<[8]}{9:<[9]}{10:<}'
    _lsofColumns = {'COMMAND': 0, 'PID': 1, 'TID': 2, 'TASKCMD': 3, 'USER': 4, 'FD': 5, 'TYPE': 6, 'DEVICE': 7,
                     'SIZE/OFF': 8, 'NODE': 9, 'NAME': 10}
    _lsofHeader = ['COMMAND', 'PID', 'TID', 'TASKCMD', 'USER', 'FD', 'TYPE', 'DEVICE', 'SIZE/OFF', 'NODE', 'NAME']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating lsof module.")
        super(lsofModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(columns=self._lsofColumns, header=self._lsofHeader, head=1,
                                               strFormat=self._lsofStrFormat)
        # super(GenericCmdModule, self).__init__(header=0)
        self.defaultCmd = 'lsof '
        self.defaultKey = "lsofwS3"
        self.defaultFlags = "-w -S 2"
        self.__NAME__ = "lsof"

    def run(self, flags=None, rerun=True, **kwargs):
        def _formatOutput(results, *args, **kwargs):
            self.parse(source=self._lsofBasicFormatter(results), **kwargs)
            return self

        command = {flags or self.defaultKey: self.defaultCmd + (flags or self.defaultFlags)}
        if not flags and 'postparser' not in kwargs:
            kwargs['postparser'] = _formatOutput

        return self.simpleExecute(command=command, rerun=rerun, **kwargs)

    def getOpenFilesByPID(self, pid=None, rerun=False, **kwargs):
        """ Returns a list of files open by a particular PID.

        - :param pid: (str) a number
        - :param rerun: (bool) default False
        - :param kwargs: passed directly to 'simpleExecute'
        - :return:
        """

        def openFilesByPIDParser(results, *args, **kwargs):
            saveResults = []
            parseNre = re.compile(r'^n/', flags=re.MULTILINE | re.DOTALL)
            for fline in results.splitlines():
                if parseNre.search(fline):
                    saveResults.append(parseNre.sub('/', fline))
            if saveResults:
                return saveResults
            return None

        kwargs['wait'] = kwargs.get('wait', 120)

        return self.simpleExecute(commandKey=f'lsofwfp{pid}', command=f'lsof -wFn -p {pid}',
                                  postparser=openFilesByPIDParser, rerun=rerun, **kwargs)

    def getOpenFilesByFilesystem(self, filesystem='/', rerun=False, **kwargs):
        """ Show a list of files associated with a specific filesystem.

        - :param filesystem: (str) a filesystem
        - :param rerun: (bool) default False
        - :param kwargs: passed directly to 'simpleExecute'
        - :return:
        """

        def parseDeletedFiles(results, *args, **kwargs):
            return BashParser(source=self._lsofBasicFormatter(re.sub(r'\s+(?=\(deleted\))', '', results,
                                                                     flags=re.MULTILINE | re.DOTALL)),
                              header=1, head=1)

        kwargs['wait'] = kwargs.get('wait', 120)

        return self.simpleExecute(commandKey=f'lsofsf{filesystem}', command=f'lsof -s +f -- {filesystem}',
                                  postparser=parseDeletedFiles, rerun=rerun, **kwargs)

    def getOpenDeletedFiles(self):
        """ Finds any files that have been deleted but not yet closed and thus stuck in the (deleted) state

        - :return:
        """
        # return self.search_by_column('TYPE', 'REG').search_by_column('NAME', '(deleted)', explicit=False)
        return self.correlation(('TYPE', 'REG', True, False), ('NAME', '(deleted)', False, False), convert=True)

    def lsofConvertResultsToBytes(self, results=None):
        """ Coverts the 'SIZE/OFF' column in the lsof output to Bytes.

        - :param results: default self
        - :return:
        """

        if results is None:
            results = self
        # print(f'lsofConvertResultsToBytes - Shortest Line: {results.shortestLine}')
        # print(f'lsofConvertResultsToBytes - Shortest Line: {results._getShortestLine(results)}')
        return self.convertResultsToBytes(results, ['SIZE/OFF'])

    def formatOpenDeletedFiles(self, maxLines=None, formatColumns=None):
        """ Outputs a list of open but deleted files that depending on the 'formatColumns' param has had the 'SIZE/OFF'
            column converted.

        - :param maxLines: limits the number of line shown.
        - :param formatColumns: determines if the output will be converted to bytes.
        - :return:
        """

        if not maxLines and not formatColumns:
            return self.lsofConvertResultsToBytes(self.getOpenDeletedFiles().sort(key='SIZE/OFF',
                                                                                  keyType=int, reverse=True)
                                                  ).formatOutput().replace('(deleted)', ' (deleted)')

        openDeletedFiles = self.getOpenDeletedFiles().sort(key='SIZE/OFF', keyType=int, reverse=True)
        if formatColumns:
            openDeletedFiles = self.trimResultsToColumns(openDeletedFiles, formatColumns)
        if maxLines and maxLines < len(openDeletedFiles) + 1:
            openDeletedFiles.parse(source=openDeletedFiles[:maxLines + 1], refreshData=True)

        return self.lsofConvertResultsToBytes(openDeletedFiles).formatOutput().replace('(deleted)', ' (deleted)')

    @staticmethod
    def _lsofBasicFormatter(results):
        """
            Best effort formatting for standard lsof output that returns a list of lists
            Expects either a string or a list of lists as input
        """

        def calc_seperaters(line):
            cSep = []
            num = 1
            activeCol = ""
            for col in line:
                if not col:
                    num += 1
                    continue
                cSep.append((activeCol, num + len(activeCol)))
                activeCol = col
                num = 1
            else:
                if activeCol:
                    cSep.append((activeCol, num + len(activeCol)))
            return cSep

        def buildNewLine(line, sSep):
            activeSepIndex = 0
            activeNum = sSep[activeSepIndex][1]
            num = 0
            newLine = []
            for word in line:
                if not word:
                    num += 1
                    if num > activeNum:
                        newLine.append('--')
                        activeSepIndex += 1
                        if activeSepIndex >= len(sSep):
                            break
                        activeNum = sSep[activeSepIndex][1]
                        num = 0
                    continue
                if word:
                    newLine.append(word)
                    num = 0
                    activeSepIndex += 1
                    if activeSepIndex >= len(sSep):
                        break
                    activeNum = sSep[activeSepIndex][1]
            return newLine

        results = [line.strip().split(' ') for line in results.splitlines()]
        cSep = calc_seperaters(results[0])

        return [buildNewLine(line, cSep) for line in results]
