#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the touch command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
import re


log = logging.getLogger('touchModule')


class touchModule(GenericCmdModule):
    """
         touchModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'touch' on remote machines.
         defaultCmd: touch
         defaultFlags = %s; echo $?
            The reason for appending echo to the command is to have a helpful way to determine if the command was
            successful.
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating touch module.")
        super(touchModule, self).__init__(tki=tki)
        self.tki.getModules('rm')
        self.defaultCmd = '/bin/touch '
        self.defaultKey = "touch%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCode, 'rerun': True}
        self.__NAME__ = "touch"
        self.requireFlags = True

    def isWritable(self, filesystem, wait=60, **kwargs):
        if not self.tki:
            return
        log.info("Testing filesystem %s to see if its writable" % filesystem)
        if re.search("/$", filesystem):
            path = filesystem + "writetest"
        else:
            path = filesystem + "/writetest"
        results = self.run(path, wait=wait, **kwargs)
        if results is None or results is False:
            return results
        elif results == "NONE":
            return Exception('An error occurred while trying to run the touch command')
        self.tki.modules.rm.runUpload(f'-rf {path}', rerun=kwargs.get('rerun', False))
        return results
