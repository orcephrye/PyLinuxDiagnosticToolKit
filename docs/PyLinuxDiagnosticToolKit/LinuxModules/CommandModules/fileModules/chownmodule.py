#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.2.0
# Date: 7/07/20
# Description: This is a module for using the chown command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('chownModule')


class chownModule(GenericCmdModule):
    """
         chownModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'chown' on remote machines.
         defaultCmd: chown
         defaultFlags = %s; echo $?
          The point of the echo tagged to the end of the chown command is to provide a feedback mechanism to easily
          determine success. The output of the command is now either None,False,True
     """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating chown module.")
        super(chownModule, self).__init__(tki=tki)
        self.defaultCmd = 'chown '
        self.defaultKey = "chown%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = "chown"
        self.requireFlags = True
