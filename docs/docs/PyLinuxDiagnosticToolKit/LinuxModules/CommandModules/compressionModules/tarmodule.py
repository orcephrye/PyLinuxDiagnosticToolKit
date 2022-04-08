#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the tar command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('tarModule')


class tarModule(GenericCmdModule):
    """
         tarModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'tar'
         on remote machines.
         defaultCmd: tar
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating tar module.")
        super(tarModule, self).__init__(tki=tki)
        self.defaultCmd = 'tar '
        self.defaultKey = "tar%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'tar'
        self.requireFlags = True
