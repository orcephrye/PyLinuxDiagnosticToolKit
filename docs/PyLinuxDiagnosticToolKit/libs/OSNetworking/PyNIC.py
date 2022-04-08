#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson
# Rackspace Hosting
# Version: 0.1.0
# Date: 02/02/21


import logging
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import exceptionDecorator as excDec
from OSNetworking import regExIPShow, regExIPName, regExMAC, regExOptions
from OSNetworking.PyIPAddress import IP4Address, IP6Address
from typing import Literal, List, Union, Tuple, Optional


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
                    level=logging.ERROR)
log = logging.getLogger('PyNIC')


class NetworkInterfaceCards(object):

    _devices = None

    def __init__(self, nicsInfo: str, dataType: Literal['ip', 'ifconfig'] = 'ip'):
        self.raw_ip_text = nicsInfo
        self.dataType = dataType
        self._devices = {}
        if dataType.lower() == 'ip':
            self._parseIPShow()
        elif dataType.lower() == 'ifconfig':
            self._parseIfConfig()

    def __str__(self) -> str:
        return self.raw_ip_text

    def _parseIPShow(self) -> None:
        nicList = [NetworkInterfaceCard(i, self.dataType) for i in regExIPShow.split(self.raw_ip_text.strip()) if i]
        for nic in nicList:
            self._devices.update({nic.name: nic})

    def _parseIfConfig(self) -> None:
        ifconfigLines = self.raw_ip_text.strip().splitlines()
        devices = []
        newDevice = []
        for line in ifconfigLines:
            if line == '':
                devices.append('\n'.join(newDevice))
                newDevice = []
            else:
                newDevice.append(line)
        if newDevice:
            devices.append('\n'.join(newDevice))
        for nic in [NetworkInterfaceCard(device, self.dataType) for device in devices]:
            self._devices.update({nic.name: nic})

    def getDeviceByName(self, name: str) -> Union[str, None]:
        return self._devices.get(name, self._devices.get(name.lower(), None))

    def getDeviceByIP(self, ipaddr: str) -> Union[str, None]:
        for dev in self.devices:
            for ip in dev.ips:
                if ipaddr in ip.raw_address:
                    return dev
        return None

    def getDeviceByMac(self, mac: str) -> Union[str, None]:
        for nic in self._devices.values():
            if nic.mac.lower() == mac.lower():
                return nic

    @property
    def names(self) -> List:
        if self._devices:
            return list(self._devices.keys())
        return []

    @property
    def devices(self) -> List:
        if self._devices:
            return list(self._devices.values())
        return []

    @property
    def ipAddress(self) -> List:
        return [ip for dev in self._devices.values() for ip in dev.ips]


class NetworkInterfaceCard(object):

    name = None
    mtu = None
    qdisc = None
    state = None
    group = None
    qlen = None
    options = None
    mac = None
    mac_brd = None
    ip4List = None
    ip6List = None
    rawData = None
    dataType = None

    def __init__(self, nicInfo: str, dataType: Literal['ip', 'ifconfig'] = 'ip'):
        self.rawData = nicInfo
        self.dataType = dataType
        self.ip4List = []
        self.ip6List = []
        if dataType.lower() == 'ip':
            self._parseIPShow()
        elif dataType.lower() == 'ifconfig':
            self._parseIfConfig()

    def __str__(self) -> None:
        return self.rawData

    def _parseIfConfig(self) -> None:
        ifconfigList = self.rawData.splitlines()
        self.name = self._getIfconfigName(ifconfigList)
        self._parseIPAddresses(ifconfigList)
        self.mac = self._parseMac(ifconfigList)[0]
        self._parseIfconfigAttr(ifconfigList)
        self._parseIfconfigOptions(ifconfigList)

    def _parseIPShow(self) -> None:
        rawName = regExIPName.match(self.rawData)
        if rawName is None:
            raise Exception('Invalid Network format')
        rawName = rawName.group()
        self.name = rawName.strip().strip(':')
        nicInfoList = self.rawData.strip().splitlines()
        self.mac, self.mac_brd = self._parseMac(nicInfoList)
        self.options = self._parseOptions(nicInfoList, rawName)
        self._parseAttrs(nicInfoList, rawName)
        self._parseIPAddresses(nicInfoList)

    def _parseIfconfigAttr(self, ifconfigList: List) -> None:
        def _parseOldFormatHelper(ifList, string):
            tmp = [i for row in ifList if string in row for i in row.split() if string in i]
            return tmp[0].split(':')[-1] if len(tmp) == 1 else None

        def _parseNewFormatHelper(ifList, string):
            tmp = [col for row in ifList if string in row for col in row.strip().split()]
            return tmp[tmp.index(string)+1]

        if 'MTU:' in self.rawData:
            self.mtu = _parseOldFormatHelper(ifconfigList, 'MTU:')
            self.qlen = _parseOldFormatHelper(ifconfigList, 'txqueuelen:')
        else:
            self.mtu = _parseNewFormatHelper(ifconfigList, 'mtu')
            self.qlen = _parseNewFormatHelper(ifconfigList, 'txqueuelen')

    @excDec()
    def _parseIfconfigOptions(self, ifconfigList: List) -> None:
        optionsRowStr = 'MTU:' if 'MTU:' in self.rawData else 'mtu'
        options = [row.split() for row in ifconfigList if optionsRowStr in row][0]
        if 'mtu' in options:
            if 'flags=' in options[options.index('mtu')-1]:
                self.options = options[options.index('mtu') - 1].split('<')[-1].strip().strip('>').split(',')
        else:
            self.options = options[:options.index(f'MTU:{self.mtu}')]
        if self.options[0] == 'UP':
            self.state = 'UP'
        else:
            self.state = 'DOWN'

    def _getIfconfigName(self, ifconfigList: List) -> str:
        for line in ifconfigList:
            m = regExIPName.match(line)
            if m:
                return m.group().strip()
        return ""

    @excDec(returnOnExcept=None)
    def _parseIPAddresses(self, nicInfoList: List) -> None:
        self.ip4List = [IP4Address(row, dataType=self.dataType) for row in nicInfoList if 'inet ' in row]
        self.ip6List = [IP6Address(row, dataType=self.dataType) for row in nicInfoList if 'inet6 ' in row]

    @excDec(returnOnExcept=None)
    def _parseAttrs(self, nicInfoList: List, rawName: str) -> None:
        infoRow = [row for row in nicInfoList if rawName in row][0]
        infoRowList = infoRow.strip().split()
        for attr in self.attributes:
            setattr(self, attr, infoRowList[infoRowList.index(attr)+1])

    @staticmethod
    @excDec(returnOnExcept="")
    def _parseOptions(nicInfoList: List, rawName: str) -> str:
        infoRow = [row for row in nicInfoList if rawName in row][0]
        options = regExOptions.search(infoRow)
        return options.group(1).split(',')

    @staticmethod
    @excDec(returnOnExcept=(None, None))
    def _parseMac(nicInfoList: str, filterStr: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        if filterStr is not None:
            macRow = [row for row in nicInfoList if filterStr in row]
        else:
            macRow = set(filter(None, [row for row in nicInfoList
                                       for fStr in ('HWaddr', 'ether', 'link/')
                                       if fStr in row]))
        if len(macRow) == 0:
            return None, None
        macRow = list(macRow)
        macInfo = None
        if macRow:
            macInfo = regExMAC.findall(macRow[0])
        if macInfo:
            return macInfo[0], macInfo[-1]
        return None, None

    @property
    def attributes(self) -> List:
        return ['mtu', 'qdisc', 'state', 'group', 'qlen']

    @property
    def ips(self) -> List:
        return self.ip4List + self.ip6List
