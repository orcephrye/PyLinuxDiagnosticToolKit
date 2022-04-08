#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for interacting with the fstab file


import logging
import re
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParser import BashParser
from PyCustomCollections.CustomDataStructures import IndexList
from libs.LDTKExceptions import exceptionDecorator


log = logging.getLogger('fstabModule')


class fstabModule(GenericCmdModule, BashParser):
    """
         fstabModule class. This class inherits from both the GenericCmdModule and BashParser. It is used to execute the
         Linux command 'cat /etc/fstab' on remote machines.
         defaultCmd: cat /etc/fstab
         defaultFlags = /etc/fstab
    """

    labelReg = re.compile('^LABEL=')
    uuidReg = re.compile('^UUID=')
    _fstabTemplate = {'Device': 0, 'MountPoint': 1, 'Type': 2, 'Options': 3, 'Flags': 4}
    _fstabHeader = ['Device', 'MountPoint', 'Type', 'Options', 'Flags']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating fstab module.")
        super(fstabModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(columns=self._fstabTemplate, header=self._fstabHeader)
        self.tki.getModules('cat', 'findfs')
        self.__NAME__ = "fstab"

    def run(self, **kwargs):

        def fstabFilter(line):
            if not line or len(line) != 6 or re.search('^#', line[0]):
                return False
            return True

        def fstabOptions(line):
            tempLine = line[0:-2]
            tempLine.append(' '.join(line[-2:]))
            tempLine[0] = self._checkForUUID(self._checkForLabel(tempLine[0]))
            del line
            return tempLine

        def parsefstab(results, *args, **kwargs):
            if results is None:
                return None
            output = list(map(fstabOptions, filter(fstabFilter, [line.split() for line in results.splitlines()])))
            self.parseInput(source=output, refreshData=True)
            return self

        return self.tki.modules.cat('/etc/fstab', postparser=parsefstab, **kwargs)

    def doesExist(self, filesystem):
        """ This is looking for the mount point in the fstab to see if it is configured.

        - :param filesystem:
        - :return:
        """

        if len(self) <= 0:
            return []
        if len(filesystem) == 1:
            if re.search("^/$", filesystem):
                reg = re.compile('^/$')
            else:
                reg = re.compile(filesystem)
        else:
            reg = re.compile(filesystem)
        for line in self:
            if reg.search(line[0]) or reg.search(line[1]):
                return IndexList([line], columns=self._fstabTemplate)
        return IndexList([[]], columns=self._fstabTemplate)

    def isKernelAware(self, mountpoint, **kwargs):
        if not mountpoint:
            return False
        if 'wait' not in kwargs:
            kwargs['wait'] = 10
        results = self.tki.modules.cat('/proc/mounts', **kwargs)
        if results is None:
            return results
        for line in results.splitlines():
            outLine = line.split()
            if outLine and len(outLine) == 6:
                if re.search(mountpoint, outLine[1]):
                    return True
        return False

    @exceptionDecorator(returnOnExcept=[])
    def mountPointToDevice(self, mountPoint):
        self.verifyNeedForRun()
        return self.getSearch(('MountPoint', mountPoint))['Device']

    @exceptionDecorator(returnOnExcept=[])
    def deviceToMountPoint(self, device):
        self.verifyNeedForRun()
        return self.getSearch(('Device', device))['MountPoint']

    @exceptionDecorator(returnOnExcept=False)
    def isType(self, filesystem, fsType):
        typeOfFS = self.whatType(filesystem)
        if type(fsType) == str:
            fsType = [fsType]
        return typeOfFS.lower().strip() in [x.lower().strip() for x in fsType]

    def whatType(self, filesystem):
        self.verifyNeedForRun()
        output = self.getSearch(('MountPoint', filesystem))
        if output:
            return output['Type'][0]
        output = self.getSearch(('Device', filesystem))
        if output:
            return output['Type'][0]
        raise Exception('Unable to find filesystem as a mount point nor as a device name')

    def _checkForLabel(self, line):
        if self.labelReg.search(line):
            return self.tki.modules.findfs.convertLABEL(line[6:], wait=60) or ""
        return line

    def _checkForUUID(self, line):
        if self.uuidReg.search(line):
            return self.tki.modules.findfs.convertUUID(line[5:], wait=60) or ""
        return line
