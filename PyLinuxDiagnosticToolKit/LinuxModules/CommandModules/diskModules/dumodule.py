#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the du command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParsers import BashParser
import re


log = logging.getLogger('duModule')


class duModule(GenericCmdModule):
    """
         duModule class. This class inherits from both the GenericCmdModule and BashParser. It is used to execute the
         Linux command 'du'
         on remote machines.
         defaultCmd: du
         defaultFlags =
    """

    checkString = re.compile('^\s*[0-9]')
    _duStrFormat = '{0:<[0]}{1:<[1]}'
    _duTemplate = {'SIZE': 0, 'FILE': 1}
    _duHeader = ['SIZE', 'FILE/DIR']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating du module.")
        super(duModule, self).__init__(tki=tki)
        self.defaultCmd = 'du '
        self.defaultKey = "du%s"
        self.defaultFlags = "%s"
        self.defaultKwargs = {}
        self.__NAME__ = 'du'
        self.requireFlags = True

    def run(self, flags=None, parseOutput=False, maxLines=0, sort=False, **kwargs):

        refreshData = True if self else None

        def parseFilesystemOutput(results, **kwargs):
            def _filterResults(line):
                if self.checkString.search(line):
                    return line
            results = "\n".join(filter(_filterResults, results.strip().splitlines()))

            obj = BashParser(strFormat=self._duStrFormat, columns=self._duTemplate, header=self._duHeader)
            if maxLines and maxLines < len(obj) + 1:
                obj.parse(source=results[:maxLines + 1], refreshData=True)
            else:
                obj.parse(source=results, refreshData=refreshData)
            if sort:
                obj.sort_by_column('SIZE', column_type=int, reverse=True)
            if parseOutput:
                return obj.convert_results_to_bytes(obj, columnList=['SIZE'], _baseSize='K')
            return obj

        self.defaultKwargs = {'postparser': parseFilesystemOutput}
        kwargs.setdefault('useDefaultParsing', kwargs.pop('useDefaultParsing', parseOutput) or parseOutput)
        return super(duModule, self).run(flags, **kwargs)
