#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the tail command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('tailModule')


class tailModule(GenericCmdModule):
    """
         tailModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'tail'
         on remote machines.
         defaultCmd: tail
         defaultFlags =
     """
    def __init__(self, tki, *args, **kwargs):
        log.info("Creating tail module.")
        super(tailModule, self).__init__(tki=tki)
        self.defaultCmd = '/usr/bin/tail '
        self.defaultKey = "tail%s"
        self.defaultFlags = "%s"
        self.__NAME__ = "tail"
        self.requireFlags = True
