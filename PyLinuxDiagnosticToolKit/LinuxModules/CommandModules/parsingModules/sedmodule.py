#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Description: This is a module for using the sed command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('sedModule')


class sedModule(GenericCmdModule):
    """
         sedModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'sed' on remote machines.
         defaultCmd: sed
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating sed module.")
        super(sedModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/sed '
        self.defaultKey = "sed%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'sed'
        self.requireFlags = True

    def run(self, flags=None, sedInput=None, *args, **kwargs):
        if sedInput:
            flags = f'{flags} <<< "{sedInput}"'
        return super(sedModule, self).run(flags, *args, **kwargs)
