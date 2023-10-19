#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson
# Rackspace Hosting
# Version: 0.1.0
# Date: 02/02/21


import logging
from OSNetworking import regExtractIP4NoMask, regExtractIP4WithMask, regExtractIP6WithMask
from OSNetworking import dottedQuadToCidrNetmask, cidrNetmaskToDottedQuad
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import exceptionDecorator as excDec
from typing import Literal, List


log = logging.getLogger('PYIPAddress')


class IP4Address(object):

    dataType = None
    raw_data = None
    raw_address = None
    address = None
    netmask = None
    bridge = None
    options = None
    __newFormat = ('inet', 'netmask', 'broadcast')
    __oldFormat = ('addr:', 'Mask:', 'Bcast:')

    def __init__(self, ip_str: str, dataType: Literal['ip', 'ifconfig'] = 'ip'):
        self.raw_data = ip_str
        self.dataType = dataType
        if dataType == 'ip':
            self._parseIP()
        elif dataType == 'ifconfig':
            self._parseIfconfig()

    def __str__(self) -> str:
        return self.raw_address

    def _parseIfconfig(self) -> None:
        def _parseHelper(tmpList, filterStr):
            tmpItem = [i.strip().split(':')[-1] for i in tmpList if filterStr in i]
            if len(tmpItem) > 0:
                return tmpItem[0]

        ipLine = self.raw_data.strip().split()
        if 'addr:' in ipLine:
            self.address, self.netmask, self.bridge = [_parseHelper(ipLine, fStr) for fStr in self.__oldFormat]
        else:
            self.address, self.netmask, self.bridge = [_parseHelper(ipLine, fStr) for fStr in self.__newFormat]
        self.raw_address = f'{self.address}/{self.netmask}'

    def _parseIP(self) -> None:
        ipStr = self.raw_data.strip()
        m = regExtractIP4WithMask.search(ipStr)
        self.raw_address = m.group().strip()
        assert len(m.groups()) == 5
        self.address = '.'.join(m.groups()[:-1])
        self.netmask = m.groups()[-1].strip('/')
        ips = regExtractIP4NoMask.findall(ipStr)
        if len(ips) > 1:
            self.bridge = '.'.join(ips[-1])
        self.options = self._parseOptions(ipStr)

    @excDec(returnOnExcept=[])
    def _parseOptions(self, ipStr) -> List:
        return ipStr.strip().split(self.raw_address if self.bridge is None else self.bridge)[-1].strip().split()

    @property
    def dottedNetmask(self) -> str:
        if not self.netmask:
            return ''
        if len(self.netmask) > 2:
            return self.netmask
        return cidrNetmaskToDottedQuad(self.netmask)

    @property
    def cidrNotation(self) -> int:
        if not self.netmask:
            return ''
        if len(self.netmask) == 2:
            return self.netmask
        return dottedQuadToCidrNetmask(self.netmask)

    @property
    def ipType(self) -> Literal['ip4']:
        return 'ip4'


class IP6Address(object):

    dataType = None
    raw_data = None
    raw_address = None
    address = None
    netmask = None
    options = None

    def __init__(self, ip_str: str, dataType: Literal['ip', 'ifconfig'] = 'ip'):
        self.raw_data = ip_str
        self.dataType = dataType
        if dataType == 'ip':
            self._parseIP()
        elif dataType == 'ifconfig':
            self._parseIfconfig()

    def __str__(self) -> str:
        return self.raw_address

    def _parseIfconfig(self) -> None:
        ipLine = self.raw_data.strip().split()
        # print(f'IP6 Parse line: {ipLine}')
        # m = regExtractIP6NoMask.search(ipLine)
        # address = self.raw_address = m.group().strip()
        if 'addr:' in ipLine:
            ip = ipLine[ipLine.index('addr:')+1]
        else:
            ip = ipLine[ipLine.index('inet6')+1]
        self.address = ip.split('/')[0]
        self.netmask = ip.split('/')[-1]
        self.options = ipLine[ipLine.index(ip)+1:]
        self.raw_address = f'{self.address}/{self.netmask}'

    def _parseIP(self) -> None:
        ipStr = self.raw_data.strip()
        m = regExtractIP6WithMask.search(ipStr)
        self.raw_address = m.group().strip()
        self.address = self.raw_address.split('/')[0]
        self.netmask = m.groups()[-1].strip('/')
        self.options = ipStr.strip().split(self.raw_address)[-1].strip().split()

    @property
    def ipType(self) -> Literal['ip6']:
        return 'ip6'
