#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the lspci command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('lspciModule')


class lspciModule(GenericCmdModule):
    """
         lspciModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'lscpci'
         on remote machines.
         defaultCmd: lspci
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating lspci module.")
        super(lspciModule, self).__init__(tki=tki)
        self.defaultCmd = 'lspci '
        self.defaultKey = "lspci%s"
        self.__NAME__ = 'lspci'

    def hasDevice(self, deviceName, wait=60, **kwargs):
        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        return self.run(f'| grep -qi {deviceName}; echo $?', wait=wait, **kwargs)
