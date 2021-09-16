#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the head command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('headModule')


class headModule(GenericCmdModule):
    """
         headModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'head'
         on remote machines.
         defaultCmd: head
         defaultFlags =
     """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating head module.")
        super(headModule, self).__init__(tki=tki)
        self.defaultCmd = '/usr/bin/head '
        self.defaultKey = "head%s"
        self.defaultFlags = "%s"
        self.__NAME__ = "head"
        self.requireFlags = True
