#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Description: This is a module for using the mkdir command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('mkdirModule')


class mkdirModule(GenericCmdModule):
    """
         mkdirModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'mkdir' on remote machines.
         defaultCmd: mkdir
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating mkdir module.")
        super(mkdirModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/mkdir '
        self.defaultKey = "mkdir%s"
        self.defaultFlags = "-p %s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = 'mkdir'
        self.requireFlags = True

    def run(self, flags, makePath=True, **kwargs):

        options = self.defaultFlags
        if not makePath:
            options = "%s"

        command = {self.defaultKey % flags: self.defaultCmd + options % flags}
        return super(mkdirModule, self).run(command, **kwargs)
