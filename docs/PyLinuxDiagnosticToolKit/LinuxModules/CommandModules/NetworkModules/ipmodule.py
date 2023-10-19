#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 06/15/17
# Description: This is a module for using the ip command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyLinuxDiagnosticToolKit.libs.OSNetworking.PyNIC import NetworkInterfaceCards
from PyLinuxDiagnosticToolKit.libs.OSNetworking.PyRoute import Routes


log = logging.getLogger('ipModule')


class ipModule(GenericCmdModule):
    """
         ipModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'ip' on remote machines.
         defaultCmd: ip
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ip module.")
        super(ipModule, self).__init__(tki=tki)
        self.defaultCmd = 'ip '
        self.defaultKey = "ip%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ip'
        self.requireFlags = True

    def getIPShowAllData(self, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 30)

        def _postParserHelper(results, *args, **kwargs):
            if not isinstance(results, str):
                return False
            return NetworkInterfaceCards(results.strip(), dataType='ip')

        kwargs.update({'postparser': _postParserHelper})

        return self.run('addr show', **kwargs)

    def getIPRouteData(self, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 30)

        def _postParserHelper(results, *args, **kwargs):
            if not isinstance(results, str):
                return False
            return Routes(results.strip(), dataType='ip')

        kwargs.update({'postparser': _postParserHelper})

        return self.run('route', **kwargs)
