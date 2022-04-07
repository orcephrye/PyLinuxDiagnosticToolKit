#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.2.0
# Date: 06/15/17


from LinuxModules.genericCmdModule import GenericCmdModule, executionDecorator
from PyCustomParsers.GenericParser import BashParser
import logging


log = logging.getLogger('hostsModule')


# TODO: Host module should either not be a bashparser or it needs work

class hostsModule(GenericCmdModule, BashParser):
    """ hostModule class. This class uses 'catModule' to get the '/etc/hosts' file. This is converted into an IndexList
        using BashParser.
    """

    returnValueType = str
    _hostsFileContents = None

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating hosts module.")
        super(hostsModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__()
        self.defaultKey = 'etchosts'
        self.__NAME__ = 'hosts'

    def __str__(self):
        return self.tki.modules.cat('/etc/hosts')

    @executionDecorator
    def run(self, *args, **kwargs):
        if kwargs.get('rerun') or not self:
            self.parseInput(self.tki.modules.cat('/etc/hosts', rerun=True), refreshData=True)
        return self
