#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the df command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParser import BashParser
from libs.LDTKExceptions import exceptionDecorator
import re


log = logging.getLogger('dfModule')


class dfModule(GenericCmdModule, BashParser):
    """
         dfModule class. This class inherits from both the GenericCmdModule and BashParser. It is used to execute the
         Linux command 'df' on remote machines.
         defaultCmd: df
         defaultFlags =
    """

    _dfTemplate = {'Filesystem': 0, '1k-Inodes': 1, 'Size': 2, 'IUsed': 3, 'Used': 4, 'IAvailable': 5, 'Available': 6,
                   'IPercentage': 7, 'Percent': 8, 'Mount': 9}
    _dfHeader = ['Filesystem', '1k-Inodes', 'Size', 'IUsed', 'Used', 'IAvailable', 'Available',
                 'IPercentage', 'Percent', 'Mount']

    def __init__(self, tki, *args, **kwargsdf):
        log.info("Creating df module.")
        super(dfModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(template=self._dfTemplate, header=self._dfHeader)
        self.defaultCmd = 'df '
        self.defaultKey = "dfCmd"
        self.defaultFlags = ""
        self.__NAME__ = 'df'

    def run(self, flags=None, **kwargs):

        def _combineLines(dfiLine, dfhLine):
            if dfiLine[0] != dfhLine[0] or dfiLine[-1] != dfhLine[-1]:
                return []
            return [dfiLine[0], dfiLine[1], dfhLine[1], dfiLine[2], dfhLine[2],
                    dfiLine[3], dfhLine[3], dfiLine[4], dfhLine[4], dfiLine[5]]

        def _formatOutput(results, *args, **kwargs):
            if 'dfi' not in results or 'df' not in results:
                return None
            dfi = [line.split() for line in dfModule._preFormatter(output=results['dfi']).splitlines()]
            dfh = [line.split() for line in dfModule._preFormatter(output=results['df']).splitlines()]
            output = []
            for x in range(1, len(dfi)):
                output.append(_combineLines(dfi[x], dfh[x]))
            self.parseInput(source=output)
            return self

        if not flags:
            command = {"%s%s" % (self.defaultCmd, ''), "%s%s" % (self.defaultCmd, '-i')}
            command = {'commandKey': self.defaultKey, 'command': command, 'postparser': _formatOutput}
            kwargs.update(command)
            if kwargs.get('rerun', False):
                self.reset()
            return self.simpleExecute(**kwargs)
        else:
            command = {flags: self.defaultCmd + flags}
            return self.simpleExecute(command=command, **kwargs)

    @exceptionDecorator(returnOnExcept=[])
    def _helperMBParser(self, indexList, threshold):
        values = list(map(int, indexList['Available']))
        return [indexList[x] for x in range(len(values)) if values[x] / 1024 <= threshold]

    @exceptionDecorator(returnOnExcept=[])
    def _helperPercentParser(self, indexList, threshold):
        values = list(map(lambda x: 100 - float(x.strip('%')), indexList['Percent']))
        return [indexList[x] for x in range(len(values)) if values[x] <= threshold]

    def _helperMountFilesystemFinder(self, filesystem=None, mountpoint=None):
        self.verifyNeedForRun()
        if not self:
            return []
        if filesystem:
            return self.getSearch(('Filesystem', filesystem))
        if mountpoint:
            return self.getSearch(('Mount', mountpoint))

    def isBelowPercentThreshold(self, threshold=5, filesystem=None, mountpoint=None):
        threshold = int(threshold)
        fileSystemIndexList = self._helperMountFilesystemFinder(filesystem, mountpoint)
        if fileSystemIndexList:
            return self._helperPercentParser(fileSystemIndexList, threshold)
        return self._helperPercentParser(self, threshold)

    def isBelowMBThreshold(self, threshold=5000, filesystem=None, mountpoint=None):
        threshold = int(threshold)
        fileSystemIndexList = self._helperMountFilesystemFinder(filesystem, mountpoint)
        if fileSystemIndexList:
            return self._helperMBParser(fileSystemIndexList, threshold)
        return self._helperMBParser(self, threshold)

    def dfConvertResultsToBytes(self):
        return self.convert_results_to_bytes(self, ['Size', 'Available', 'Used'], _baseSize='K')

    @staticmethod
    def _preFormatter(output=None):
        # preformats the df output so that each entry appears on a single line
        # this is to prevent the IndexList, IndexTable, and KeyedList from crashing when __get__ is called
        if not output:
            return {}
        output, baseLine = dfModule._preFormatHelper(output.splitlines())
        baseDict = dict(enumerate(output))
        for num, line in baseDict.items():
            numLine = len(line.split())
            # if the length of the line is less than the length of the header line
            # and it exists and the next line exists
            if numLine < baseLine and baseDict.get(num) and baseDict.get(num + 1):
                # if the sum of the length of the current line
                # and that of the next line equal the length of the header line
                if (numLine + len(baseDict[num + 1].split())) == baseLine:
                    baseDict[num] += ' ' + baseDict[num + 1]  # combine the current line and the next line
                    del baseDict[num + 1]  # delete the next line
                    num += 1  # increment
        return '\n'.join(baseDict.values())

    @staticmethod
    def _preFormatHelper(output):
        # this will ensure that any errors appearing before the header line in the command output will be clipped
        baseLine = 0
        for sline in range(len(output)):
            # this will always shorted the affected line by one
            baseLine = len(re.sub('Mount[a-z]*? [a-z][a-z]$', 'Mounted', output[sline]).split())
            if baseLine == len(output[sline].split()) - 1:
                if sline > 0:
                    output = output[sline:]
                break
        return output, baseLine
