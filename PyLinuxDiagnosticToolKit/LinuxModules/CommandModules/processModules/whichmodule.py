#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 02.0
# Date: 6/06/17
# Description: This is a module for using the which command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('whichModule')


class whichModule(GenericCmdModule):
    """
        whichModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
        'which' on remote machines.
        defaultCmd: which
        defaultFlags = '%s; echo $?' - The 'echo $?' is used along with the '_formateExitCode'.
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating which module.")
        super(whichModule, self).__init__(tki=tki)
        self.defaultCmd = '/usr/bin/which '
        self.defaultKey = "%s"
        self.defaultFlags = "%s; echo $?"
        self.defaultKwargs = {'postparser': GenericCmdModule._formatExitCodeStr}
        self.__NAME__ = "which"
        self.requireFlags = True

    def doesCommandExist(self, command, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 10)
        return self.run(command, postparser=GenericCmdModule._formatExitCode, **kwargs)
