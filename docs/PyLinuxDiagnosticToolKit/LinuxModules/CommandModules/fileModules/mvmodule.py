#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Description: This is a module for using the mv command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('pgrepModule')


class mvModule(GenericCmdModule):
    """
         mvModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'mv' on remote machines.
         defaultCmd: mv
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating mv module.")
        super(mvModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/mv '
        self.defaultKey = "mv%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = 'mv'
        self.requireFlags = True
