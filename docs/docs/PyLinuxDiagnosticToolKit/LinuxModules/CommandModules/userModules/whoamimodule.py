#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the whoami command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('whoamiModule')


class whoamiModule(GenericCmdModule):
    """
        whoamiModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
        'whoami' on remote machines.
        defaultCmd: whoami
        defaultFlags =
        This module by default will only provide the current user of whatever thread is available. To see what the
        current user of a thread is you will have to provide that threads UUID as a parameter channelIDReq.
    """

    username = ""

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating whoami module.")
        super(whoamiModule, self).__init__(tki=tki)
        self.defaultCmd = 'whoami'
        self.defaultKey = "whoami%s"
        self.defaultFlags = ""
        self.defaultKwargs = {'postparser': self._safeOutput, 'rerun': True}
        self.__NAME__ = 'whoamiCmd'

    def __str__(self):
        return self.username

    def _safeOutput(self, results, *args, **kwargs):
        if isinstance(results, str):
            self.username = results
        return results
