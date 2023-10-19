#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson
# Rackspace Hosting
# Version: 0.1.0
# Date: 02/02/21


import logging
from OSNetworking import regExtractIP6NoMask, dottedQuadToCidrNetmask
from typing import Any, Literal, List


log = logging.getLogger('PyRoute')


class Routes(object):

    raw_route_text = None
    dataType = None
    routes = None
    _default = None

    def __init__(self, routeData: str, dataType: Literal['ip', 'route'] = 'ip'):
        self.raw_route_text = routeData.strip()
        self.dataType = dataType
        if dataType.lower() == 'ip':
            self._parseIPRoute()
        elif dataType.lower() == 'route':
            self._parseRouteN()

    def __str__(self) -> str:
        return self.raw_route_text

    def _parseIPRoute(self) -> None:
        self.routes = [Route(route) for route in self.raw_route_text.splitlines()]

    def _parseRouteN(self) -> None:
        self.routes = [Route(route, dataType=self.dataType) for route in self.raw_route_text.splitlines()
                       if 'Destination' not in route and 'Kernel' not in route]

    def getRouteByNetwork(self, network: str) -> str:
        for route in self.routes:
            if route.network == network:
                return route

    def getRoutesByDev(self, dev: str) -> List:
        return [route for route in self.routes if route.dev == dev]

    def getRoutesViaIP(self, via: str) -> List:
        return [route for route in self.routes if route.via == via]

    def getRoutesWithOption(self, option: str) -> List:
        return [route for route in self.routes if option in route.options]

    @property
    def default(self) -> Any:
        if self._default is not None:
            return self._default
        for route in self.routes:
            if route.isDefault:
                self._default = route
                return route
        return None


class Route(object):

    dataType = None
    raw_route = None
    network = None
    via = None
    dev = None
    options = None

    def __init__(self, routeData: str, dataType: Literal['ip', 'route'] = 'ip'):
        self.raw_route = routeData.strip()
        self.dataType = dataType
        if dataType.lower() == 'ip':
            self._parseIPRoute()
        elif dataType.lower() == 'route':
            self._parseRouteN()

    def __str__(self) -> str:
        return self.raw_route

    def _parseIPRoute(self) -> None:
        routeList = self.raw_route.split()
        self.network = routeList[0]
        if 'via' in routeList:
            self.via = routeList[routeList.index('via')+1]
        self.dev = routeList[routeList.index('dev')+1]
        self.options = routeList[routeList.index('dev')+2:]

    def _parseRouteN(self) -> None:
        routeList = self.raw_route.split()
        self.dev = routeList[-1].strip()
        self.via = routeList[1].strip()
        networkMask = dottedQuadToCidrNetmask(routeList[2].strip())
        self.network = f'{routeList[0].strip()}/{str(networkMask)}' if networkMask else routeList[0].strip()
        options = "Flags:%s Metric:%s Ref:%s Use:%s" % tuple(routeList[3:-1])
        self.options = options.strip().split()

    @property
    def gateway(self) -> str:
        return self.via

    @property
    def isDefault(self) -> bool:
        return True if self.network == 'default' or self.network == '0.0.0.0' else False

    @property
    def isIPv6(self) -> bool:
        return True if regExtractIP6NoMask.search(str(self.network)) is not None else False
