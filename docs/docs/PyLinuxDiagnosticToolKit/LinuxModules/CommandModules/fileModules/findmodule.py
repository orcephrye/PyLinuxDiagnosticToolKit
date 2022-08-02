#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the find command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParser import BashParser
import re


log = logging.getLogger('findModule')


class findModule(GenericCmdModule, BashParser):
    """
         findModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'find'
         on remote machines.
         defaultCmd: find
         defaultFlags =
     """

    checkString = re.compile('^\s*[0-9]')
    _findStrFormat = '{0:<[0]}{1:<[1]}'
    _findTemplate = {'SIZE': 0, 'FILE': 1}
    _findHeader = ['SIZE', 'FILE']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating find module.")
        super(findModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__()
        self.defaultCmd = '/usr/bin/find '
        self.defaultKey = "find%s"
        self.defaultFlags = "%s"
        self.defaultKwargs = {}
        self.__NAME__ = "find"
        self.requireFlags = True

    def run(self, flags=None, parseOutput=False, maxLines=0, **kwargs):
        def parseFilesystemOutput(results, **kwargs):
            def _filterResults(line):
                if self.checkString.search(line):
                    return line
            results = "\n".join(filter(_filterResults, results.strip().splitlines()))

            def _parseFilesystemOutput(parserObject):
                if parseOutput:
                    parserObject.parseInput(source=results, strFormat=self._findStrFormat, columns=self._findTemplate,
                                            header=self._findHeader, refreshData=refreshData)
                    parserObject.sort(key='SIZE', keyType=int, reverse=True)
                    if maxLines and maxLines < len(parserObject) + 1:
                        parserObject.parseInput(source=parserObject[:maxLines + 1], refreshData=True)
                    return self.convert_results_to_bytes(parserObject, columnList=['SIZE'], _baseSize='K')
                parserObject.parseInput(source=results, refreshData=refreshData)
                return parserObject
            if flags:
                return _parseFilesystemOutput(BashParser())
            return _parseFilesystemOutput(self)
        refreshData = True if self else None
        self.defaultKwargs = {'postparser': parseFilesystemOutput}
        kwargs.setdefault('useDefaultParsing', kwargs.pop('useDefaultParsing', parseOutput) or parseOutput)
        return super(findModule, self).run(flags, **kwargs)
