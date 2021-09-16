#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the ll command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.GenericParser import BashParser
from PyCustomParsers.dateparseline import DateParseLine as DPL
import pytz
import pytz.reference


log = logging.getLogger('llModule')


class llModule(GenericCmdModule, BashParser):
    """
         llModule class. This class inherits from both the GenericCmdModule and BashParser. It is used to execute the
         Linux command 'll' on remote machines.
         defaultCmd: /usr/bin/ls
         defaultFlags = -l %s
            Instead of using the '-l' or 'long' flag you can pass longListing=False.
                However this removes the ability to parse the output.
     """

    _llheader = ['Perms', 'Link', 'Name', 'Group', 'Size', 'Date', 'Time', 'FileName']
    _llcolumns = {'Perms': 0, 'NumLink': 1, 'Name': 2, 'Group': 3, 'Size': 4, 'Date': 5, 'Time': 6,  'FileName': 7}

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating ll module.")
        super(llModule, self).__init__(tki=tki, columns=self._llcolumns, header=self._llheader)
        # log.info('Creating BashParser')
        # super(GenericCmdModule, self).__init__(columns=self._llcolumns, header=self._llheader)
        log.info('Finished creating BashParser')
        self.defaultCmd = 'ls '
        self.defaultKey = "ls%s"
        self.defaultFlags = "-l %s"
        self.requireFlags = True

    # noinspection PyMethodOverriding
    def run(self, flags, parse=True, longListing=True, **kwargs):

        def _formatOutput(results=None, **kwargs):
            if not results:
                log.error("An error happened while running ls command.")
                return None
            return BashParser(source=self._parseLSTime(results), columns=self._llcolumns, header=self._llheader)

        options = self.defaultFlags
        if not longListing:
            options = "%s"

        command = {self.defaultKey % flags: self.defaultCmd + options % flags}
        if parse and longListing is True and 'postparser' not in kwargs:
            kwargs['postparser'] = _formatOutput
        return self.simpleExecute(command=command, **kwargs)

    def fileExist(self, filename, **kwargs):
        kwargs.update({'wait': kwargs.pop('wait', 120) or 120})

        def _postfileExist(results, *args, **kwargs):
            return self.tki.sshCon.escapeChars.sub('', results).strip().startswith(filename)

        return self.run(flags=filename, parse=False, longListing=False, postparser=_postfileExist, **kwargs)

    def isFileEmpty(self, filename, **kwargs):
        kwargs.update({'postparser': GenericCmdModule._formatExitCode, 'wait': kwargs.pop('wait', 120) or 120})
        return self.simpleExecute(f"[ ! -s {filename} ]; echo $?", commandKey=f'isFileEmpty{filename}', **kwargs)

    def _parseLSTime(self, lsOut):
        output = ""
        lsOutList = [item.split() for item in lsOut.splitlines()]
        remoteTZ = self.tki.getModules('os').getTimeZone()
        remoteTZ = remoteTZ if remoteTZ else pytz.reference.LocalTimezone()
        dp = None

        def _parseHelper(dpItem, tmpList):
            dpItem.dateStr = ' '.join(tmpList[5:8])
            if len(dpItem.dateStr.split()) > 2:
                dpItem.dateStr = ''.join(dpItem.dateStr[0:2]) + " " + dpItem.dateStr[-1]
            dpItem.dateSliceCoordinates = (5, 8)
            return dpItem

        for row in lsOutList:
            if 'total' in row[0]:
                continue
            if getattr(dp, 'dateTime', None) is None:
                tmpDP = DPL(line=row, tzinfos=remoteTZ, checkPast=False, mode='SCAN', sliceNums=(5, None))
            elif hasattr(dp, 'parseOtherLine'):
                tmpDP = dp.parseOtherLine(row)
                if getattr(tmpDP, 'dateTime', None) is None:
                    tmpDP = DPL(line=row, tzinfos=remoteTZ, checkPast=False, mode='SCAN', sliceNums=(5, None))
            else:
                tmpDP = DPL(line=row, tzinfos=remoteTZ, checkPast=False, mode='SCAN', sliceNums=(5, None))

            if getattr(tmpDP, 'dateTime', None) is None:
                dp = _parseHelper(tmpDP, row)
            else:
                dp = tmpDP

            output += f"{' '.join(row[0:dp.dateSliceCoordinates[0]])} " \
                      f"{str(dp) if getattr(dp, 'dateTime', None) is not None else dp.dateStr} " \
                      f"{' '.join(row[dp.dateSliceCoordinates[-1]:])}\n"
        return output
