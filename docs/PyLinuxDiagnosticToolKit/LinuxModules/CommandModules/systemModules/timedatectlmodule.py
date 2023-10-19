#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.1.0
# Date: 6/09/21
# Description: This is a module for using the timedatectl command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('timedatectlModule')


class timedatectlModule(GenericCmdModule):
    """
        timedatectlModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
        'timedatectl' on remote machines.
        defaultCmd: timedatectl
        defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating timedatectl module.")
        super(timedatectlModule, self).__init__(tki=tki)
        self.defaultCmd = 'timedatectl '
        self.defaultKey = "timedatectl%s"
        self.defaultFlags = "status"
        self.defaultKwargs = {'preparser': self.doesCommandExistPreParser}
        self.__NAME__ = 'timedatectl'
        self.requireFlags = False

    def getTimezone(self, *args, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 10)
        output = self.run(*args, **kwargs)
        if not isinstance(output, str):
            return ""
        timezoneLine = [item for item in output.splitlines() if 'Time zone:' in item]
        if len(timezoneLine) == 0:
            return ""
        timezoneLineWords = [column.strip() for column in timezoneLine[0].strip().split()]
        return timezoneLineWords[2]
