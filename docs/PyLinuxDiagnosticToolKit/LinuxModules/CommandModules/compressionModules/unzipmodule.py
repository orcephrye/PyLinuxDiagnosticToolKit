#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the unzip command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('unzipModule')


class unzipModule(GenericCmdModule):
    """
         unzipModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'unzip' on remote machines.
         defaultCmd: unzip
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating unzip module.")
        super(unzipModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/unzip '
        self.defaultKey = "unzip%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'unzip'
        self.requireFlags = True
