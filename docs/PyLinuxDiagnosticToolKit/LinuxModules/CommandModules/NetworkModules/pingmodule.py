#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.2.0
# Date: 06/15/17


import logging
from collections.abc import Iterable
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('pingModule')


class pingModule(GenericCmdModule):
    """
        pingModule class. This class inherits both GenericCmdModule and BashParser. It is used to execute the Linux
        command 'ping' on remote machines.
        defaultCmd: ping
        defaultFlags = -c %s -W %s %s
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ping module.")
        super(pingModule, self).__init__(tki=tki)
        self.defaultCmd = '/bin/ping '
        self.defaultKey = 'ping%s'
        self.defaultFlags = '-c %s -W %s %s'
        self.defaultKwargs = {'rerun': True}
        self.__NAME__ = 'ping'
        self.requireFlags = True

    def run(self, hostIp, pingCount=1, pingWait=5, *args, **kwargs):
        """ Returns a list of unreachable hosts
            Takes a string, list, or dict
            Host addresses must be provided in the string, list, or dict values
            Dict keys will be used as the commandKey/name of the command object
        """

        pingCmdDict = {}
        if isinstance(hostIp, str):
            pingCmdDict.update(
                {self.defaultKey % hostIp: self.defaultCmd + self.defaultFlags % (pingCount, pingWait, hostIp)}
            )
        elif isinstance(hostIp, dict):  # provide a name or label for each address as the key
            for hostKey, hostValue in hostIp.items():
                pingCmdDict.update(
                    {hostKey: self.defaultCmd + self.defaultFlags % (pingCount, pingWait, hostValue)}
                )
        elif isinstance(hostIp, Iterable):
            for pingHost in hostIp:
                pingCmdDict.update(
                    {self.defaultKey % pingHost: self.defaultCmd + self.defaultFlags % (pingCount, pingWait, pingHost)}
                )
        return super(pingModule, self).run(pingCmdDict, *args, **self.mergeKwargs(kwargs, self.defaultKwargs))

    def canPing(self, hostIp, *args, **kwargs):
        kwargs['wait'] = kwargs.get('wait', 120)

        def _canPingStrFilter(results=None, *args, **kwargs):
            return ' 0% packet loss' in results

        def _canPingDictFilter(results=None, *args, **kwargs):
            return {k: _canPingStrFilter(v) for k, v in results.items()}

        def _canPingListFilter(results=None, *args, **kwargs):
            return [_canPingStrFilter(p) for p in results]

        if isinstance(hostIp, str) or len(hostIp) == 1:
            kwargs.update(self.updatekwargs('postparser', _canPingStrFilter, **kwargs))
        elif isinstance(hostIp, dict):
            kwargs.update(self.updatekwargs('postparser', _canPingDictFilter, **kwargs))
        elif isinstance(hostIp, Iterable):
            kwargs.update(self.updatekwargs('postparser', _canPingListFilter, **kwargs))
        return self.run(hostIp, *args, **kwargs)
