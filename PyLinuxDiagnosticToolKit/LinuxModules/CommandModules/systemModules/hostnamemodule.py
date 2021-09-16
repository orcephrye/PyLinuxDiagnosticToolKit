#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.2.0
# Date: 07/29/2020
# Description: This is a module for using the hostname command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('hostnameModule')


class hostnameModule(GenericCmdModule):
    """
         hostnameModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'hostname'
         on remote machines.
         defaultCmd: hostname
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating hostname module.")
        super(hostnameModule, self).__init__(tki=tki)
        self.defaultCmd = 'hostname '
        self.defaultKey = "hostname%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'hostname'
        self.requireFlags = False
