#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine, Shashank Bhatt

# Version: 0.2.0
# Date: 27/08/2020
# Description: This is a module for using the getfacl command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('getfaclModule')


class getfaclModule(GenericCmdModule):
    """
         getfaclModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'getfacl' on remote machines.
         defaultCmd: getfacl
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating getfacl module.")
        super(getfaclModule, self).__init__(tki=tki)
        self.defaultCmd = 'getfacl '
        self.defaultKey = "getfacl%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'getfacl'
        self.requireFlags = True

    def isFacl(self, filename, wait=60, **kwargs):
        def _parseFacl(result=None, **kwargs):
            if not isinstance(result, str):
                log.error("The result is not the string so quiting the process ")
                return None
            if result.count("user") > 1:
                return True
            if result.count("group") > 2:
                return True
            if result.count("other") > 1:
                return True
            return False

        kwargs.update({"postparser": _parseFacl})

        return self.simpleExecute(command=f"getfacl {filename}", commandKey="isFacl%s", wait=wait, **kwargs)
