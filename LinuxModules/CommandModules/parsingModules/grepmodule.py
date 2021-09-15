#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Description: This is a module for using the grep command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('grepModule')


class grepModule(GenericCmdModule):
    """
         grepModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'grep' on remote machines.
         defaultCmd: grep
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating grep module.")
        super(grepModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/grep '
        self.defaultKey = "grep%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'grep'
        self.requireFlags = True

    def run(self, flags=None, grepInput=None, *args, **kwargs):
        if grepInput:
            flags = f'{flags} <<< "{grepInput}"'
        return super(grepModule, self).run(flags, *args, **kwargs)
