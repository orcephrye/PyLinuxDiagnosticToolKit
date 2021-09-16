#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the bcu command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('bcuModule')


class bcuModule(GenericCmdModule):
    """
         bcuModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'bcu'
         on remote machines.
         defaultCmd: bcu
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating bcu module.")
        super(bcuModule, self).__init__(tki=tki)
        self.defaultCmd = 'bcu '
        self.defaultKey = "bcu%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'bcu'
        self.requireFlags = True
