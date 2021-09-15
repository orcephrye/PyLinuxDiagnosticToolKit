#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the kill command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.PyCustomParsers.GenericParser import BashParser
import re


log = logging.getLogger('findmntModule')


class findmntModule(GenericCmdModule, BashParser):
    """
         findmntModule class. This class inherits from both the GenericCmdModule and BashParser. It is used to execute
         the  Linux command 'findmnt' on remote machines.
         defaultCmd: findmnt
         defaultFlags = -nl --output TARGET,SOURCE
    """

    _findmntStrFormat = "{0:<[0]}{1:<}"
    _findmntTemplate = {'SOURCE': 0, 'TARGET': 1}
    _findmntHeader = ['SOURCE', 'TARGET']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating findmnt module.")
        super(findmntModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(template=self._findmntTemplate,
                                               header=self._findmntHeader,
                                               strFormat=self._findmntStrFormat)
        self.defaultCmd = 'findmnt '
        self.defaultKey = "findmntCmd"
        self.defaultFlags = "-nl --output TARGET,SOURCE"
        self.defaultKwargs = {'postparser': self._findmntFormatOutput}
        self.__NAME__ = "findmnt"

    @staticmethod
    def cmdFilter(inputStr):
        return len(inputStr) == 2

    def _findmntFormatOutput(self, results, *args, **kwargs):
        if not results:
            return None
        results = filter(findmntModule.cmdFilter, [x.split() for x in results.splitlines() if x != ''])
        self.parseInput(source=results)
        return self

    def isMountBind(self, mountpoint, **kwargs):
        if not self:
            return None
        mountEntry = self.getSearch('TARGET', mountpoint, **kwargs)
        if not mountEntry:
            return False
        for source in mountEntry['SOURCE']:
            if re.search('\\[', source):
                return True
        return False
