#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/08/21
# Description: This is a module for using the ifconfig command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyLinuxDiagnosticToolKit.libs.OSNetworking.PyNIC import NetworkInterfaceCards


log = logging.getLogger('ifconfigModule')


class ifconfigModule(GenericCmdModule):
    """
         ifconfigModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'ifconfig' on remote machines.
         defaultCmd: ifconfig
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ifconfig module.")
        super(ifconfigModule, self).__init__(tki=tki)
        self.defaultKwargs = {'preparser': self.doesCommandExistPreParser}
        self.defaultCmd = 'ifconfig '
        self.defaultKey = "ifconfig%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ifconfig'

    def getIfconfigAllData(self, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 30)
        kwargs.update(self.defaultKwargs)

        def _postParserHelper(results, *args, **kwargs):
            if not isinstance(results, str):
                return False
            return NetworkInterfaceCards(results.strip(), dataType='ifconfig')

        kwargs.update({'postparser': _postParserHelper})

        return self.run('-a', **kwargs)
