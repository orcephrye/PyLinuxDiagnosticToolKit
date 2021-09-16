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
from PyCustomParsers.GenericParser import BashParser


log = logging.getLogger('lsofModule')


class lsofModule(GenericCmdModule, BashParser):
    """
        lsofModule class. This class inherits both GenericCmdModule and BashParser. It is used to execute the Linux
        command 'lsof' on remote machines.
        defaultCmd: lsof
        defaultFlags = -w -S 2
    """

    _lsofStrFormat = '{0:<[0]}{1:<[1]}{2:<[2]}{3:<[3]}{4:<[4]}{5:<[5]}{6:<[6]}{7:<[7]}{8:<[8]}{9:<}'
    _lsofTemplate = {'COMMAND': 0, 'PID': 1, 'TID': 2, 'USER': 3, 'FD': 4, 'TYPE': 5, 'DEVICE': 6,
                     'SIZE/OFF': 7, 'NODE': 8, 'NAME': 9}
    _lsofHeader = ['COMMAND', 'PID', 'TID', 'USER', 'FD', 'TYPE', 'DEVICE', 'SIZE/OFF', 'NODE', 'NAME']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating lsof module.")
        super(lsofModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(template=self._lsofTemplate, header=self._lsofHeader,
                                               strFormat=self._lsofStrFormat)
        self.defaultCmd = 'lsof '
        self.defaultKey = "lsofwS3"
        self.defaultFlags = "-w -S 2"
        self.__NAME__ = "lsof"

    def run(self, flags=None, rerun=True, **kwargs):
        def _formatOutput(results, *args, **kwargs):
            self.parseInput(source=self._lsofBasicFormatter(results), **kwargs)
            return self

        command = {flags or self.defaultKey: self.defaultCmd + (flags or self.defaultFlags)}
        if not flags and 'postparser' not in kwargs:
            kwargs['postparser'] = _formatOutput

        return self.simpleExecute(command=command, rerun=rerun, **kwargs)

    def getLSOFOutput(self, rerun=False):
        """ Backwards compatibility method with older 'processModule'.

        - :param rerun: (bool) default True
        - :return:
        """

        return self.run(rerun=rerun)

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
            self.parseInput(source=self._lsofBasicFormatter(re.sub('\s+(?=\(deleted\))', '', results,
                                                                   flags=re.MULTILINE | re.DOTALL)), **kwargs)
            return self

        return self.simpleExecute(commandKey=f'lsofsf{filesystem}', command=f'lsof -s +f -- {filesystem}',
                                  postparser=parseDeletedFiles, rerun=rerun, **kwargs)

    def getOpenDeletedFiles(self):
        """ Finds any files that have been deleted but not yet closed and thus stuck in the (deleted) state

        - :return:
        """

        return self.getSearch(('TYPE', 'REG')).getSearch(('NAME', '(deleted)'), explicit=False)

    def lsofConvertResultsToBytes(self, results=None):
        """ Coverts the 'SIZE/OFF' column in the lsof output to Bytes.

        - :param results: default self
        - :return:
        """

        if results is None:
            results = self
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
            openDeletedFiles.parseInput(source=openDeletedFiles[:maxLines + 1], refreshData=True)

        return self.lsofConvertResultsToBytes(openDeletedFiles).formatOutput().replace('(deleted)', ' (deleted)')

    @staticmethod
    def _lsofBasicFormatter(results):
        """
            Best effort formatting for standard lsof output that returns a list of lists
            Expects either a string or a list of lists as input
        """

        def _formatHelper(rowList):
            row = str(rowList)
            if len(rowList) == 9 or 'deleted' in rowList[-1] or \
               'IPv' in row and ('TCP' or 'UDP' or 'RPC') in row and len(rowList) == 10:
                rowList.insert(2, '')
            if 'raw6' in row and '->' in row and len(rowList) == 10:
                rowList.insert(5, '')
            return rowList

        def _formatFilter(row):
            if len(row) != 10:
                return False
            return True

        if type(results) is list:
            return list(filter(_formatFilter, map(_formatHelper, results)))
        return list(filter(_formatFilter, map(_formatHelper, map(str.split, results.splitlines()))))
