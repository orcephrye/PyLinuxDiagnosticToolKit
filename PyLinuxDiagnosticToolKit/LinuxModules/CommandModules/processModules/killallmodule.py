#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the killall command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('killallModule')


class killallModule(GenericCmdModule):
    """
        Execute the Linux command 'killall' on remote machines
        defaultCmd: killall
        defaultFlags = '%s; echo $?' - The 'echo $?' is used along with the '_formateExitCode'.
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating killall module.")
        super(killallModule, self).__init__(tki=tki)
        self.killAllCmd = '/usr/bin/killall '
        self.defaultKey = "%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.requireFlags = True
