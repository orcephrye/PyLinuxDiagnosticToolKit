#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Description: This is a module for using the awk command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('awkModule')


class awkModule(GenericCmdModule):
    """
         awkModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'awk' on remote machines.
         defaultCmd: awk
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating awk module.")
        super(awkModule, self).__init__(tki=tki)
        self.defaultCmd = '/usr/bin/awk '
        self.defaultKey = "awk%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'awk'
        self.requireFlags = True

    def run(self, flags=None, awkInput=None, *args, **kwargs):
        if awkInput:
            flags = f'{flags} <<< "{awkInput}"'
        return super(awkModule, self).run(flags, *args, **kwargs)
