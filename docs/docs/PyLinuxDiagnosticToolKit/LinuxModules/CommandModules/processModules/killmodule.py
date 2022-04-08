#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the kill command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('killModule')


class killModule(GenericCmdModule):
    """
        Execute the Linux command 'kill' on remote machines
        defaultCmd: kill
        defaultFlags = '%s; echo $?' - The 'echo $?' is used along with the '_formateExitCode'.
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating kill module.")
        super(killModule, self).__init__(tki=tki)
        self.defaultCmd = '/usr/bin/kill '
        self.defaultKey = "%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = "kill"
        self.requireFlags = True
