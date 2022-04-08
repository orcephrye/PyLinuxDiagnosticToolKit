#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/08/21
# Description: This is a module for using the ifdown command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('ifdownModule')


class ifdownModule(GenericCmdModule):
    """
         ifdownModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'ifdown' on remote machines.
         defaultCmd: ifdown
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ifdown module.")
        super(ifdownModule, self).__init__(tki=tki)
        self.defaultCmd = 'ifdown '
        self.defaultKey = "ifdown%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ifdown'
