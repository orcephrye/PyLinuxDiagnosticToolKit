#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the uptime command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from datetime import timedelta

log = logging.getLogger('uptimeModule')


class uptimeModule(GenericCmdModule):
    """
        uptimeModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
        'uptime'
        on remote machines.
        defaultCmd: uptime
        defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating uptime module.")
        super(uptimeModule, self).__init__(tki=tki)
        self.defaultCmd = 'uptime '
        self.defaultKey = "uptime%s"
        self.defaultFlags = ""
        self.__NAME__ = 'uptime'
        self.requireFlags = False

    def getUptimeViaProc(self, parse=True, wait=60, **kwargs):
        kwargs['rerun'] = kwargs.get('rerun', True)
        kwargs.update({"command": "awk '{print $1}' /proc/uptime", 'wait': wait})
        if parse:
            kwargs.update({'postparser': uptimeModule._parseUptime})
        return self.simpleExecute(**kwargs)

    def rebootedWithin(self, timeInSeconds):

        def _convertSeconds(strToConvert):
            try:
                return float(strToConvert)
            except:
                return 0.0

        if type(timeInSeconds) is not int or type(timeInSeconds) is not float:
            return False

        seconds = self.getUptimeViaProc(parse=False, rerun=True)
        if not isinstance(seconds, str):
            return False
        seconds = _convertSeconds(strToConvert=seconds)
        if seconds == 0.0:
            return False

        return seconds <= timeInSeconds

    @staticmethod
    def _parseUptime(results, *args, **kwargs):
        if not isinstance(results, str):
            return None

        try:
            return str(timedelta(seconds=float(results.strip())))
        except Exception:
            return None
