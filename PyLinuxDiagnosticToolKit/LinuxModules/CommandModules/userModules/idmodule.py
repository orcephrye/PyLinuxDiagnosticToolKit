#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.1.0
# Date: 7/12/16
# Description: This is a module for using the id command.


import logging
import re
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomCollections import NamespaceDict


log = logging.getLogger('idModule')


class idModule(GenericCmdModule):
    """
         idModule class. This class inherits from both the GenericCmdModule and NamespaceDict. It is used to execute the
         Linux command 'id' on remote machines.
         defaultCmd: id
         defaultFlags =
     """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating id module.")
        super(idModule, self).__init__(tki=tki)
        self.defaultCmd = 'id '
        self.defaultKey = "idMain"
        self.defaultFlags = ""
        self.defaultWait = 10
        self.__NAME__ = "id"

    def __str__(self):
        if hasattr(self, 'idMain'):
            return str(self.idMain.results)
        return ""

    def run(self, flags=None, **kwargs):
        """
            This runs the 'id' command remotely on a server and then parses the output and stores the data in this
            class.
        - :param flags: (str) i.e: UUID or username
        - :param kwargs: passed directly to 'simpleExecute'
        - :return:
        """

        def _formatOutput(results, **kwargs):
            if not results:
                return False
            if 'o such user' in results:
                return False
            output = dict((x.split('=')) for x in [i.strip() for i in results.split()])
            if 'uid' not in output or 'gid' not in output or 'groups' not in output:
                return False
            output['uid'] = re.sub(r'\([^)]*\)', '', output['uid'])
            gidUsernames = re.findall(r'\([^)]*\)', output['gid'])
            groupsUsernames = re.findall(r'\([^)]*\)', output['groups'])
            gidIds = re.findall('\d+', output['gid'])
            groupsIds = re.findall('\d+', output['groups'])
            if not gidUsernames or not groupsUsernames or not gidIds or not groupsIds:
                return False
            if len(gidUsernames) != len(gidIds) or len(groupsUsernames) != len(groupsIds):
                log.info("The group information may be wrong")
            gidUsernames = [i.replace('(', '').replace(')', '') for i in gidUsernames]
            groupsUsernames = [i.replace('(', '').replace(')', '') for i in groupsUsernames]
            output['gid'] = dict(zip(gidIds, gidUsernames))
            output['groups'] = dict(zip(groupsIds, groupsUsernames))
            idO = idObject()
            idO.update(output)
            return idO

        command = {flags or self.defaultKey: self.defaultCmd + (flags or self.defaultFlags)}
        if 'postparser' not in kwargs:
            kwargs['postparser'] = _formatOutput
        return self.simpleExecute(command=command, **kwargs)


class idObject(NamespaceDict):

    def __init__(self, *args, **kwargs):
        super(idObject, self).__init__(*args, **kwargs)

    def __str__(self):
        if 'gid' not in self or 'uid' not in self or 'groups' not in self:
            return ""
        return f"UID: {self.uid}  GID: {self.gid}  Groups: {self.groups}"
