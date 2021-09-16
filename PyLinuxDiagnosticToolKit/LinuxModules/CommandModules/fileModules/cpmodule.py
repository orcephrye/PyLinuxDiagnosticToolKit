#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the cp command.


import logging
import os
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('cpModule')


class cpModule(GenericCmdModule):
    """
         cpModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'cp'
         on remote machines.
         defaultCmd: cp
         defaultFlags = %s; echo $?
          The point of the echo tagged to the end of the cp command is to provide a feedback mechanism to easily
          determine success. The output of the command is now either None,False,True
     """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating cp module.")
        super(cpModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/cp '
        self.defaultKey = "cp%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = "cp"
        self.requireFlags = True

    def makeBackup(self, filePathName, backupPath=None, backupExt=None, **kwargs):
        if not filePathName:
            log.error('No file provided!')
            return None
        if backupExt is None:
            backupExt = '.bck'
        if backupPath is None:
            backupPath = filePathName + backupExt
        if not cpModule._detectExtension(backupPath):
            backupPath += "/" + os.path.basename(filePathName) + backupExt

        def backupPostParser(results, *args, **kwargs):
            if not isinstance(results, str):
                return None
            if len(results.splitlines()) > 0:
                log.error('Failed to back up the file!')
                return False
            return True
        return self.simpleExecute(command=f'/bin/cp -f {filePathName} {backupPath} 2>&1',
                                  postparser=backupPostParser, **kwargs)

    @staticmethod
    def _detectExtension(fileName):
        return '' if fileName.endswith('/') else os.path.splitext(fileName)[1]
