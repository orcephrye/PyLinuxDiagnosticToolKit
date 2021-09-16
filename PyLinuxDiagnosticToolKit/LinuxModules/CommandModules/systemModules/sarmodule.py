#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 4/1/19
# Description: This is a module for using the sar command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('sarModule')


class sarModule(GenericCmdModule):
    """
         sarModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'sar'
         on remote machines.
         defaultCmd: sar
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating sar module.")
        super(sarModule, self).__init__(tki=tki)
        self.defaultCmd = 'sar '
        self.defaultKey = "sar%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'sar'
        self.requireFlags = True
