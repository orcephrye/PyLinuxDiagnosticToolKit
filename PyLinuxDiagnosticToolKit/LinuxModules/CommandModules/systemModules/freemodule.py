#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 04/04/2019
# Description: This is a module for using the free command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('freeModule')


class freeModule(GenericCmdModule):
    """
         freeModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'free'
         on remote machines.
         defaultCmd: free
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating free module.")
        super(freeModule, self).__init__(tki=tki)
        self.defaultCmd = 'free '
        self.defaultKey = "free%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'free'
        self.requireFlags = False
