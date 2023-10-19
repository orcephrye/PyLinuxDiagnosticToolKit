#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/08/21
# Description: This is a module for using the ss command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('ssModule')


class ssModule(GenericCmdModule):
    """
         ssModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'ss' on remote machines.
         defaultCmd: ss
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ss module.")
        super(ssModule, self).__init__(tki=tki)
        self.defaultKwargs = {'preparser': self.doesCommandExistPreParser}
        self.defaultCmd = 'ss '
        self.defaultKey = "ss%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ss'
