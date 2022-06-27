#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the find command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParsers import BashParser
import re


log = logging.getLogger('findModule')


class findModule(GenericCmdModule):
    """
         findModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'find'
         on remote machines.
         defaultCmd: find
         defaultFlags =
     """

    checkString = re.compile(r'^\s*[0-9]')
    _findStrFormat = '{0:<[0]}{1:<[1]}'
    _findColumns = {'SIZE': 0, 'FILE': 1}
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

    def listLargestFilesOnFilesystem(self, filesystem, head=30, sort=True, **kwargs):
        def parseFindOutput(results, **kwargs):
            def _filterResults(line):
                if self.checkString.search(line):
                    return line

            results = "\n".join(filter(_filterResults, results.strip().splitlines()))

            obj = BashParser(strFormat=self._findStrFormat, columns=self._findColumns, header=self._findHeader)
            obj.parse(source=results, refreshData=True)
            if sort:
                obj.sort(key='SIZE', keyType=int, reverse=True)
            if head and head < len(obj) + 1:
                obj.parse(source=results[:head + 1], refreshData=True)
            return obj.convertResultsToBytes(obj, columnList=['SIZE'], _baseSize='B')

        kwargs.update({'postparser': parseFindOutput})

        return super(findModule, self).run(f'{filesystem} ' + "-mount -type f -ls | awk '{print $7,$NF}'", **kwargs)



