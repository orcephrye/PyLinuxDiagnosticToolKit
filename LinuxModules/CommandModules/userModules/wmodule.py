#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the w command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('wModule')


class wModule(GenericCmdModule):
    """
         wModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'w'
         on remote machines.
         defaultCmd: w
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating w module.")
        super(wModule, self).__init__(tki=tki)
        self.defaultCmd = 'w '
        self.defaultKey = "w%s"
        self.defaultFlags = ""
        self.__NAME__ = 'w'
