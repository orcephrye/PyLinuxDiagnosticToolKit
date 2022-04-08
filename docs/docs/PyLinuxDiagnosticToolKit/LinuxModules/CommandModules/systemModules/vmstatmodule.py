#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.2.0
# Date: 04/04/2019
# Description: This is a module for using the vmstat command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParser import GenericInputParser
from collections import OrderedDict


log = logging.getLogger('vmstatModule')
convertBytes = GenericInputParser.convertBytes


class vmstatModule(GenericCmdModule):
    """
         vmstatModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'vmstat' on remote machines.
         defaultCmd: vmstat
         defaultFlags =
    """

    vmstatParsedResults = None

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating vmstat module.")
        super(vmstatModule, self).__init__(tki=tki)
        self.vmstatParsedResults = OrderedDict([('total memory', ''), ('used memory', ''), ('active memory', ''),
                                                ('inactive memory', ''), ('free memory', ''), ('buffer memory', ''),
                                                ('swap cache', ''), ('total swap', ''), ('used swap', ''),
                                                ('free swap', '')])
        self.defaultCmd = 'vmstat '
        self.defaultKey = "vmstat%s"
        self.defaultKwargs = {'postparser': self._vmstatPostParser}
        self.defaultFlags = "-s -S k"
        self.__NAME__ = 'vmstat'
        self.requireFlags = False

    def _vmstatPostParser(self, results, *args, **kwargs):
        if not isinstance(results, str):
            return False
        tmpResults = [i for i in results.strip().splitlines()]
        for key in self.vmstatParsedResults.keys():
            for line in tmpResults:
                if key in line:
                    self.vmstatParsedResults[key] = line.strip().split()[0]
        return results

    def parseVmstat(self, convert=True, field=None):
        self.run(wait=60)

        def _parseField(tmpField):
            tmpField = tmpField.strip()
            if len(tmpField.split()) == 2:
                field1, field2 = tmpField.lower().split()
                field2 = str.upper(field2[0])+field2[1:]
                tmpField = field1+field2
            if hasattr(self, tmpField):
                return tmpField
            return ''

        if isinstance(field, str):
            fieldValue = _parseField(field)
            if convert:
                return f"{convertBytes(int(getattr(self, fieldValue, 0)), _baseSize='K')} {field}"
            return f"{getattr(self, fieldValue, '')} k {field}"
        if convert:
            return "\n".join([f"\t{convertBytes(int(item), _baseSize='K')} {key}"
                              for key, item in self.vmstatParsedResults.items()])
        return "\n".join([f"\t{item} k {key}" for key, item in self.vmstatParsedResults.items()])

    @property
    def totalMemory(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('total memory')

    @property
    def usedMemory(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('used memory')

    @property
    def activeMemory(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('active memory')

    @property
    def inactiveMemory(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('inactive memory')

    @property
    def freeMemory(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('free memory')

    @property
    def bufferMemory(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('buffer memory')

    @property
    def swapCache(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('swap cache')

    @property
    def totalSwap(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('total swap')

    @property
    def usedSwap(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('used swap')

    @property
    def freeSwap(self):
        self.run(wait=60)
        return self.vmstatParsedResults.get('free swap')
