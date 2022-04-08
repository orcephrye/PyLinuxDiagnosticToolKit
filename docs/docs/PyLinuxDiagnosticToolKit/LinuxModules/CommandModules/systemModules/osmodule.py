#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.4
# Date: 02/19/15


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomCollections.CustomDataStructures import IndexList
import re

log = logging.getLogger('osModule')


class osModule(GenericCmdModule):
    """
         osModule class. This class inherits from the GenericCmdModule. This module breaks the normal convention of
         CommandModules. (There always has to be an exception). This module runs a series of useful informational
         commands like uname and 'cat /proc/uptime'.
         defaultCmd: multiple commands review the variable __COMMAND__
         defaultFlags =
     """

    __COMMAND__ = {'systemInfo': '/bin/cat /proc/uptime; /bin/uname -r; /bin/uname -p; /bin/uname -n; '
                                 '/bin/cat /etc/issue /etc/redhat-release /etc/centos-release /etc/SuSE-release 2> '
                                 '/dev/null'}
    __OSTYPES__ = {'Red\s*?hat': "RedHat",
                   'Cent\s*?OS': "CentOS",
                   'Open\s*?SuSE': "OpenSuSE",
                   'Ubuntu': "Ubuntu"}

    __SUPPORTED_OS_VERSIONS__ = \
        {'Red\s*?hat': ['6', '7', '8'],
        'Cent\s*?OS': ['6', '7', '8'],
        'Open\s*?SuSE': [],
        'Ubuntu': ['16', '18', '20']}

    __SUPPORTED__ = ['rhel', 'redhat', 'red hat', 'centos', 'cent os', 'ubuntu']

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating Operating System Command Module")
        super(osModule, self).__init__(tki=tki)
        self.__fullName = None
        self.__name = None
        self.__version = None
        self.__versionName = None
        self.__majorV = None
        self.__minorV = None
        self.__timezone = None
        self.__kernelVersion = None
        self.__hostName = None
        self.__architecture = None
        self.__isCluster = None
        self.tki.getModules('cat', 'tail', 'service', 'uptime', 'timedatectl', 'uname', 'll')
        self.modules = self.tki.modules
        self.__NAME__ = "os"

    def __str__(self):
        return self._prettyStrFormat()

    def run(self, *args, **kwargs):
        def _issueParser(results, **kwargs):
            fullName = None
            name = None
            for key, v in self.__OSTYPES__.items():
                m = re.search(key, results, re.IGNORECASE)
                if m:
                    for line in results.splitlines():
                        if m.group() in line:
                            fullName = line
                    name = v
                    break
            if name is None:
                return None, None
            fullName.strip()
            version = re.search("\\d{1,2}\\.\\d{1,2}(\\.\\d{1,2})?", results)
            version = "" if version is None else version.group().strip()
            versionName = re.search("\\(\\w+\\)", fullName)
            versionName = "" if versionName is None else versionName.group().strip('(').strip(')')
            if version:
                majorVersion = version.split('.')[0]
                minorVersion = version.split('.')[-1]
            else:
                majorVersion = minorVersion = ""
            return fullName, name, version, versionName, majorVersion, minorVersion

        def _osReleaseParser(results, **kwargs):
            variables = {'NAME': "", 'VERSION': "", 'ID': "", 'VERSION_ID': "", 'PRETTY_NAME': ""}
            for line in results.strip().splitlines():
                if '=' not in line:
                    continue
                rows = line.strip().split('=')
                if rows[0].strip() in variables:
                    variables[rows[0].strip()] = rows[1].strip().strip('"')
            fullName = variables['PRETTY_NAME']
            name = None
            for key, v in self.__OSTYPES__.items():
                m = re.search(key, variables['NAME'], re.IGNORECASE)
                if m:
                    name = v
                    break
            if name is None:
                name = variables['NAME']
            version = variables['VERSION_ID']
            versionName = re.search("\\(\\w+\\)", variables['VERSION'])
            versionName = "" if versionName is None else versionName.group().strip('(').strip(')')
            if version:
                majorVersion = version.split('.')[0]
                minorVersion = version.split('.')[-1]
            else:
                majorVersion = minorVersion = ""
            return fullName, name, version, versionName, majorVersion, minorVersion

        if self.modules.ll.fileExist('/etc/os-release') and not self.modules.ll.isFileEmpty('/etc/os-release'):
            osinfo = self.modules.cat('/etc/os-release', postparser=_osReleaseParser)
        else:
            osinfo = self.modules.cat('/etc/issue /etc/redhat-release /etc/centos-release '
                                      '/etc/SuSE-release 2> /dev/null', postparser=_issueParser)

        if not isinstance(osinfo, tuple) or len(osinfo) != 6:
            return '', '', '', '', '', ''

        self.__kernelVersion = self.modules.uname.getKernelVersion()
        self.__hostName = self.modules.uname.getHostName()
        self.__architecture = self.modules.uname.getArch()

        self.__fullName, self.__name, self.__version, self.__versionName, self.__majorV, self.__minorV = osinfo
        return self.__fullName, self.__name, self.__version, self.__versionName, self.__majorV, self.__minorV

    def getOSInfo(self, *args, **kwargs):
        """ Depreciated run method for backward compatibility """
        return self.run(*args, **kwargs)

    def isOSSupported(self, supportedList=None):
        if supportedList is None:
            supportedList = self.__SUPPORTED__

        osname = str(self.osName)

        def supportedFilter(item):
            return item.lower() == osname.lower()

        return len(filter(supportedFilter, supportedList)) > 0

    def getCluster(self, **kwargs):
        """ The purpose is to determine if the server is a RHCS.
            TODO: This only works on RHEL 6 and older machines.

        - :return:
        """

        results = self.modules.service('cman', status=True, **kwargs)
        if not results:
            log.error("There was an error in executing the command by default returning False.")
            self.__isCluster = False
        if re.search('running', results) or re.search('stopped', results):
            self.__isCluster = True
        self.__isCluster = False
        return self.__isCluster

    def getUptime(self, formatted=False, parse=True, rerun=True):
        if formatted:
            return self.modules.uptime(rerun=rerun)
        return self.modules.uptime.getUptimeViaProc(parse=parse, rerun=rerun)

    def rebootedWithin(self, timeInSeconds):
        return self.modules.uptime.rebootedWithin(timeInSeconds)

    def tailVarLog(self, **kwargs):
        keyedLog = IndexList()
        logFile = '/var/log/messages'
        if 'ubuntu' in self.osName.lower():
            logFile = '/var/log/syslog'
        rawLog = self.modules.tail(logFile, wait=60)
        if not rawLog:
            return None
        keyedLog.extend([x.split() for x in rawLog.splitlines()])
        return keyedLog

    def getTimeZone(self, wait=60, **kwargs):

        def _parseRHELSysClock(results, **kwargs):
            if not isinstance(results, str):
                return ""
            for line in results.splitlines():
                if 'ZONE' in line and '#' not in line:
                    zoneStr = line.split('=')[-1]
                    return zoneStr.replace('"', '')
            return ""

        def _parseSuSESysClock(results, **kwargs):
            if not isinstance(results, str):
                return ""
            for line in results.splitlines():
                if 'TIMEZONE' in line:
                    zoneStr = line.split('=')[-1]
                    return zoneStr.replace('"', '')
            return ""

        if self.__name is None:
            self.run()

        if self.__timezone:
            return self.__timezone
        elif self.modules.which.doesCommandExist('timedatectl'):
            self.__timezone = self.modules.timedatectl.getTimezone(wait=30)
        elif self.osName.lower() == 'ubuntu':
            self.__timezone = self.modules.cat('/etc/timezone', wait=wait)
        elif self.osName.lower() == 'red hat' or self.osName.lower() == 'cent os':
            self.__timezone = self.modules.cat('/etc/sysconfig/clock', wait=wait, postparser=_parseRHELSysClock)
        elif self.osName.lower() == 'open suse':
            self.__timezone = self.modules.cat('/etc/sysconfig/clock', wait=wait, postparser=_parseSuSESysClock)

        return self.__timezone if self.__timezone else ""

    @property
    def isCluster(self):
        return self.getCluster() if self.__isCluster is None else self.__isCluster

    @property
    def timezone(self):
        return self.__timezone if self.__timezone else self.getTimeZone()

    @property
    def osName(self):
        if self.__name is None:
            self.run()
        return self.__name

    @property
    def fullOSText(self):
        if self.__fullName is None:
            self.run()
        return self.__fullName

    @property
    def version(self):
        if self.__version is None:
            self.run()
        return self.__version

    @property
    def versionName(self):
        if self.__versionName is None:
            self.run()
        return self.__versionName

    @property
    def majorVersion(self):
        if self.__majorV is None:
            self.run()
        return self.__majorV

    @property
    def minorVersion(self):
        if self.__minorV is None:
            self.run()
        return self.__minorV

    @property
    def kernelVersion(self):
        if self.__kernelVersion is None:
            self.run()
        return self.__kernelVersion

    @property
    def hostname(self):
        if self.__hostName is None:
            self.run()
        return self.__hostName

    @property
    def hardwardArchitecture(self):
        if self.__architecture is None:
            self.run()
        return self.__architecture

    @property
    def uptimeInSeconds(self):
        try:
            return float(self.getUptime(formatted=False, parse=False, rerun=False))
        except:
            return 0.0

    @property
    def uptimeAsString(self):
        return self.getUptime(formatted=False, parse=True, rerun=False)

    @property
    def uptimeViaCommand(self):
        return self.getUptime(formatted=True, rerun=False)

    def _prettyStrFormat(self):
        if self.__name is None:
            self.run()

        return f"{self.uptimeViaCommand}\nFull Name: {self.fullOSText}\n" \
               f"OS Name: {self.osName} - Version: {self.version} ({self.versionName})\n" \
               f"The Kernel is: {self.kernelVersion}\n" \
               f"The Arch is: {self.hardwardArchitecture}\nThe Hostname is: {self.hostname}\n"
