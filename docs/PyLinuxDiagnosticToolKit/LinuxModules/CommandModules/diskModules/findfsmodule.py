#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for interacting with the findfs file


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('findfsModule')


class findfsModule(GenericCmdModule):
    """
         findfsModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         'findfs' on remote machines.
         defaultCmd: findfs
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating findfs module.")
        super(findfsModule, self).__init__(tki=tki)
        self.defaultCmd = 'findfs '
        self.defaultKey = "%s"
        self.defaultFlags = "%s"
        self.__NAME__ = "findfs"
        self.requireFlags = True

    def convertUUID(self, uuid, **kwargs):
        """ This is to take UUIDs for disks and convert to the 'dev'.

        - :param uuid:
        - :return:
        """

        kwargs['wait'] = kwargs.get('wait', 30)
        flags = f'UUID={uuid}'
        command = {self.defaultKey % flags: self.defaultCmd + self.defaultFlags % flags}
        return self.simpleExecute(command=command, **kwargs)

    def convertLABEL(self, label, **kwargs):
        """ This is to take LABEL for disks and and covert to the 'dev'.

        - :param label:
        - :return:
        """

        kwargs['wait'] = kwargs.get('wait', 30)
        flags = f'LABEL={label}'
        command = {self.defaultKey % flags: self.defaultCmd + self.defaultFlags % flags}
        return self.simpleExecute(command=command, **kwargs)
