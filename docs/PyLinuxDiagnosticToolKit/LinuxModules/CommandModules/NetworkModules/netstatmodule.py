#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/08/21
# Description: This is a module for using the netstat command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('netstatModule')


class netstatModule(GenericCmdModule):
    """
         netstatModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'netstat' on remote machines.
         defaultCmd: netstat
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating netstat module.")
        super(netstatModule, self).__init__(tki=tki)
        self.defaultKwargs = {'preparser': self.doesCommandExistPreParser}
        self.defaultCmd = 'netstat '
        self.defaultKey = "netstat%s"
        self.defaultFlags = "-ntlp"
        self.__NAME__ = 'netstat'
