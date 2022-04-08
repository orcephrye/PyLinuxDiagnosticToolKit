#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/08/21
# Description: This is a module for using the ifup command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('ifupModule')


class ifupModule(GenericCmdModule):
    """
         ifupModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'ifup' on remote machines.
         defaultCmd: ifup
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ifup module.")
        super(ifupModule, self).__init__(tki=tki)
        self.defaultCmd = 'ifup '
        self.defaultKey = "ifup%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ifup'
