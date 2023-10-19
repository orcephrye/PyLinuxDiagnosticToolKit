#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for interacting with the mtab file


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParsers import BashParser
import re


log = logging.getLogger('mtabModule')


class mtabModule(GenericCmdModule, BashParser):
    """
         mtabModule class. This class inherits from both the GenericCmdModule and BashParser. It is used to execute the
         Linux command 'cat /etc/mtab' on remote machines.
         defaultCmd: cat
         defaultFlags = /etc/mtab
    """

    _mtabTemplate = {'Device': 0, 'MountPoint': 1, 'Type': 2, 'Flags': 3, 'Options': 4}
    _mtabHeader = ['Device', 'MountPoint', 'Type', 'Flags', 'Options']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating mtab module.")
        super(mtabModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(columns=self._mtabTemplate, header=self._mtabHeader)
        self.__NAME__ = 'mtab'

    def run(self, **kwargs):

        def mtabFilter(line):
            if not line or len(line) != 6 or re.search('^#', line[0]):
                return False
            return True

        def mtabOptions(line):
            tempLine = line[0:-2]
            tempLine.append(' '.join(line[-2:]))
            del line
            return tempLine

        def parsemtab(results, *args, **kwargs):
            if results is None:
                return None
            output = list(map(mtabOptions, filter(mtabFilter, [line.split() for line in results.splitlines()])))
            self.parse(source=output)
            return self

        return self.tki.modules.cat('/etc/mtab', postparser=parsemtab, **kwargs)

    def doesExist(self, filesystem):
        """
            This is looking for the mount point in the fstab to see if it is configured.
        :param filesystem:
        :return:
        """
        self.verifyNeedForRun()
        if len(filesystem) == 1:
            if re.search("^/$", filesystem):
                reg = re.compile('^/$')
            else:
                reg = re.compile(filesystem)
        else:
            reg = re.compile(filesystem)
        for line in self:
            if reg.search(line[0]) or reg.search(line[1]):
                return line
        return []
