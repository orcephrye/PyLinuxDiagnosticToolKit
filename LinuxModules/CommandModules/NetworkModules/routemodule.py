#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/08/21
# Description: This is a module for using the route command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from OSNetworking.PyRoute import Routes


log = logging.getLogger('routeModule')


class routeModule(GenericCmdModule):
    """
         routeModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'route' on remote machines.
         defaultCmd: route
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating route module.")
        super(routeModule, self).__init__(tki=tki)
        self.defaultCmd = 'route '
        self.defaultKey = "route%s"
        self.defaultKwargs = {'preparser': self.doesCommandExistPreParser}
        self.defaultFlags = ""
        self.__NAME__ = 'route'

    def getRouteData(self, **kwargs):
        def _postParserHelper(results, *args, **kwargs):
            if not isinstance(results, str):
                return False
            return Routes(results.strip(), dataType='ip')

        kwargs.update({'postparser': _postParserHelper})

        return self.run('-n', **kwargs)
