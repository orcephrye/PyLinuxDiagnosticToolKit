#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the powermt command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('powermtModule')


class powermtModule(GenericCmdModule):
    """
         powermtModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'powermt' on remote machines.
         defaultCmd: powermt
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating powermt module.")
        super(powermtModule, self).__init__(tki=tki)
        self.defaultCmd = 'powermt '
        self.defaultKey = "powermt%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'powermt'
        self.requireFlags = True
