#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the wc command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('wcModule')


class wcModule(GenericCmdModule):
    """
         wcModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'wc'
         on remote machines.
         defaultCmd: wc
         defaultFlags =
     """
    def __init__(self, tki, *args, **kwargs):
        log.info("Creating wc module.")
        super(wcModule, self).__init__(tki=tki)
        self.defaultCmd = '/usr/bin/wc '
        self.defaultKey = "wc%s"
        self.defaultFlags = "%s"
        self.__NAME__ = "wc"
        self.requireFlags = True

    def getNumberofLines(self, file="", **kwargs):

        def _postParser(results, *args, **kwargs):
            if not results:
                return None
            try:
                return int(results.strip().lower().split()[0])
            except:
                return False

        kwargs.update({'postparser': _postParser, 'wait': 60})

        return self.run(" -l " + file, **kwargs)
