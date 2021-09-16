#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Description: This is a module for using the pgrep command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('pgrepModule')


class pgrepModule(GenericCmdModule):
    """
         pgrepModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'pgrep' on remote machines.
         defaultCmd: pgrep
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating pgrep module.")
        super(pgrepModule, self).__init__(tki=tki)
        self.defaultCmd = '/usr/bin/pgrep '
        self.defaultKey = "pgrep%s"
        self.defaultFlags = "%s"
        self.defaultKwargs = {'rerun': True}
        self.__NAME__ = 'pgrep'
        self.requireFlags = True
