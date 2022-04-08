#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the rm command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('rmModule')


class rmModule(GenericCmdModule):
    """
         rmModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'rm'
         on remote machines.
         defaultCmd: rm
         defaultFlags = %s; echo $?
            The reason for appending echo to the command is to have a helpful way to determine if the command was
            successful.
     """
    def __init__(self, tki, *args, **kwargs):
        log.info("Creating rm module.")
        super(rmModule, self).__init__(tki=tki)
        self.defaultCmd = 'rm '
        self.defaultKey = "rm%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = 'rm'
        self.requireFlags = True
