#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.2.0
# Date: 7/07/20
# Description: This is a module for using the chmod command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('chmodModule')


class chmodModule(GenericCmdModule):
    """
         chmodModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'chmod' on remote machines.
         defaultCmd: chmod
         defaultFlags = %s; echo $?
          The point of the echo tagged to the end of the chmod command is to provide a feedback mechanism to easily
          determine success. The output of the command is now either None,False,True
     """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating chmod module.")
        super(chmodModule, self).__init__(tki=tki)
        self.defaultCmd = 'chmod '
        self.defaultKey = "chmod%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = "chmod"
        self.requireFlags = True
