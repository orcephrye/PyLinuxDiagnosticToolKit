#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the kill command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParsers import BashParser
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
    _findmntTemplate = {'TARGET': 0, 'SOURCE': 1}
    _findmntHeader = ['TARGET', 'SOURCE']

    # noinspection PyArgumentList
    def __init__(self, tki, *args, **kwargs):
        log.info("Creating findmnt module.")
        super(findmntModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(columns=self._findmntTemplate,
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
        results = list(filter(findmntModule.cmdFilter, [x.split() for x in results.splitlines() if x != '']))
        self.parse(source=results)
        return self

    def isMountBind(self, mount, **kwargs):
        self.verifyNeedForRun(**kwargs)
        for result in self.correlation(('SOURCE', mount), **kwargs)['SOURCE']:
            if re.search('\\[', result):
                return True
        for result in self.correlation(('TARGET', mount), **kwargs)['SOURCE']:
            if re.search('\\[', result):
                return True
        return False
