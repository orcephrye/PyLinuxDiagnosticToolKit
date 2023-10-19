#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.1.0
# Date: 6/09/21
# Description: This is a module for using the uname command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('unameModule')


class unameModule(GenericCmdModule):
    """
        unameModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
        'uname' on remote machines.
        defaultCmd: uname
        defaultFlags = -a
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating uname module.")
        super(unameModule, self).__init__(tki=tki)
        self.defaultCmd = 'uname '
        self.defaultKey = "uname%s"
        self.defaultFlags = "-a"
        self.__NAME__ = 'uname'
        self.requireFlags = False

    def getKernelVersion(self, *args, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 10)
        return self.run('-r', **kwargs)

    def getHostName(self, *args, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 10)
        return self.run('-n', **kwargs)

    def getArch(self, *args, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 10)
        return self.run('-i', **kwargs)