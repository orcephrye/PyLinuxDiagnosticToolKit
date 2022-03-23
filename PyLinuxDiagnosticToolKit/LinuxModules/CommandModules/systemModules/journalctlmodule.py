#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/01/19
# Description: This is a module for using the journalctl command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('journalctlModule')


class journalctlModule(GenericCmdModule):
    """
        journalctlModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
        'journalctl' on remote machines.
        defaultCmd: journalctl
        defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating journalctl module.")
        super(journalctlModule, self).__init__(tki=tki)
        self.defaultCmd = 'journalctl '
        self.defaultKey = "journalctl%s"
        self.defaultFlags = "-l --no-pager --utc --since yesterday"
        self.defaultKwargs = {'requirements': self.hasJournalctl,
                              'requirementsCondition': False}
        self.__NAME__ = 'journalctl'
        self.requireFlags = False

    def journalctlWithFlags(self, extraFlags, **kwargs):
        flags = self.defaultFlags + str(extraFlags).strip()
        kwargs.update(self.defaultKwargs)
        return self.run(flags, **kwargs)

    def hasJournalctl(self, *args, **kwargs):
        return self.tki.getModules('which').doesCommandExist('journalctl')
