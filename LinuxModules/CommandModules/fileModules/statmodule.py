#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine, Shashank Bhatt

# Version: 0.2.0
# Date: 26/08/2020
# Description: This is a module for using the stat command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('statModule')


class statModule(GenericCmdModule):
    """
         statModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'stat'
         on remote machines.
         defaultCmd: stat
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating stat module.")
        super(statModule, self).__init__(tki=tki)
        self.defaultCmd = 'stat '
        self.defaultKey = "stat%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'stat'
        self.requireFlags = True

    def getOwner(self, filename, wait=60, **kwargs):
        flags = "-c '%U' " + str(filename)
        return self.simpleExecute(command=f"stat {flags}", commandKey="getOwner%s", wait=wait, **kwargs)

    def getPermission(self, filename, wait=60, **kwargs):
        flags = "-L -c '%a' " + str(filename)
        return self.simpleExecute(command=f"stat {flags}", commandKey="getPermission%s", wait=wait, **kwargs)
