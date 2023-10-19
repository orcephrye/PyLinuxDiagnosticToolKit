#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the diff command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('diffModule')


class diffModule(GenericCmdModule):
    """
         diffModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'diff'
         on remote machines.
         defaultCmd: diff
         defaultFlags =
     """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating diff module.")
        super(diffModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/diff '
        self.defaultKey = "diff%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'diff'
        self.requireFlags = True
