#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the gzip command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('gzipModule')


class gzipModule(GenericCmdModule):
    """
         gzipModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'gzip'
         on remote machines.
         defaultCmd: gzip
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating gzip module.")
        super(gzipModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/gzip '
        self.defaultKey = "gzip%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'gzip'
        self.requireFlags = True
