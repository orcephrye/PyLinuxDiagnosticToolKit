#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 2/01/19
# Description: This is a module for interacting with '/var/log/messages'


import logging
import re
from datetime import datetime, timedelta
from dateutil import tz
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.dateparseline import DateParseLine as DPL


log = logging.getLogger('messagesModule')


class messagesModule(GenericCmdModule):
    """
         messageModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
            'tail -n 15000 /var/log/messages' on remote machines. It also has other methods for interacting with the
            log file.
         defaultCmd: tail
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating messages module.")
        super(messagesModule, self).__init__(tki=tki)
        self.tail = tki.getModules('tail')
        self.ll = tki.getModules('ll')
        self.timedatectl = tki.getModules('timedatectl')
        self.defaultCmd = ' '
        self.defaultKey = "messages%s"
        self.defaultFlags = " "
        self.defaultKwargs = {'requirements': self._messageRequirement, 'requirementsCondition': False}
        self.messageDate = None
        self.__NAME__ = 'messages'
        try:
            self.remoteTZ = self.timedatectl.getTimezone(wait=10)
            if self.remoteTZ != '':
                self.remoteTZ = tz.gettz(self.remoteTZ)
            else:
                self.remoteTZ = tz.gettz('/etc/localtime') or tz.gettz('UTC')
        except:
            log.warning("Failed to get parse timezone defaulting to local timezone.")
            self.remoteTZ = tz.gettz('/etc/localtime') or tz.gettz('UTC')
        self.requireFlags = False

    def run(self, *args, **kwargs):
        """
            Override 'run' method from 'GenericCmdModule' class. This is to add a postparser and to enforce a higher
            then normal wait. This also uses the 'tail' module.
        - :param args: passed to 'tail' class.
        - :param kwargs: passed to 'tail' class.
        - :return: string
        """

        kwargs.update({'postparser': self._getTimeStamp, 'wait': 180})
        kwargs.update(self.defaultKwargs)
        return self.tail('-n 15000 /var/log/messages', **kwargs)

    def makeLogEntry(self, logMessage, options="", wait=10, **kwargs):
        """
            This is use to add log entries via the 'logger' system log.
        - :param logMessage: The message passed to the syslog.
        - :param options: flags for the 'logger' command
        - :return: None
        """
        if wait:
            self.tki.execute('logger %s %s' % (options, logMessage),
                             preparser=self.doesCommandExistPreParser).waitForResults(wait=wait)
        else:
            self.tki.execute('logger %s %s' % (options, logMessage), preparser=self.doesCommandExistPreParser)

    def getLogsWithinTimeRange(self, trange='25 minutes ago', targetTime=None):
        """
            Uses text via the 'trange' variable and a target time frame to determine the time range to pull log lines.
            This method uses a series of private methods as helper methods.
        - :param trange: (str) This excepts a string that determines the time frame to pull logs. The first text should
            be a number value. While the second word should be a unit of time such as seconds or minutes. (The 's' is
            optional. The finial/third word is optional and either exists as 'ago' or doesn't. Without the word 'ago'
            this makes the targetTime the middle while 'ago' makes the targetTime the 'end'.
        - :param targetTime: This is the time at which the range uses as reference.
        - :return:
        """

        if not isinstance(targetTime, datetime):
            targetTime = datetime.now(tz=self.remoteTZ)
        start, end = messagesModule._parseTimeRange(trange=trange, targetTime=targetTime)
        numberOfLines = self._getNumberOfLines()
        logsWithinTime = ""
        for lines in self._messageGenerator(numberOfLines):
            if not isinstance(lines, str):
                break
            parseLines, continueCondition = self._parseMessageLines(lines, start, end)
            if parseLines:
                logsWithinTime += "\n".join(reversed(parseLines))
            if not continueCondition:
                break
        return logsWithinTime

    def _messageRequirement(self, *args, **kwargs):
        return self.doesFileExistRequirement('/var/log/messages')

    def _parseMessageLines(self, lines, start, end):
        """
            Helper function for 'getLogsWithinTimeRange'. This appends all lines within a log file that has a
            timestamp within the given time range.
        - :param lines: string
        - :param start: datetime object
        - :param end: datetime object
        - :return: (tuple) first index is a list, second index is a bool
        """

        linesWithinTime = []

        if not self.messageDate:
            log.debug("No message Date present. Running 'getTimeStamp'.")
            self._getTimeStamp(lines.strip().splitlines()[:-9])

        log.debug("Searching for dates between: %s and %s" % (start, end))

        for line in reversed(lines.strip().splitlines()):
            dateT = self._getTimeWithMessageDate(line)
            if isinstance(dateT, datetime):
                if messagesModule.timeInRange(start, end, dateT):
                    linesWithinTime.append(line)
                elif dateT < start:
                    return linesWithinTime, False
        return linesWithinTime, True

    def _messageGenerator(self, numberOfLines):
        """
            Helper method of 'getLogsWithinTimeRange' method. This method acts as a generator and is meant to be used
            in a for loop. Uses tail to pull the last 1000 lines of '/var/log/messages' remote file and then continues
            to pull 1000 more lines each time.
        - :param numberOfLines: (int) this should be the total length of the log file.
        - :return: yields string
        """

        x = 1000
        command = "awk 'NR==%s, NR==%s; NR==%s {print; exit}' /var/log/messages"
        if numberOfLines <= 1000:
            numberOfLines = 0
            yield self.tail('-n 1000 /var/log/messages', wait=120, rerun=True)
        numberOfLines -= x
        while numberOfLines >= 0:
            tmpCommand = command % (numberOfLines, numberOfLines+999, numberOfLines+1000)
            yield self.simpleExecute(tmpCommand, commandKey='awk%s' % numberOfLines, wait=180, rerun=True)
            if numberOfLines == 0:
                break
            elif numberOfLines < 1000:
                x += numberOfLines
                numberOfLines = 0
            else:
                x += 1000
                numberOfLines -= 1000

    def _getNumberOfLines(self):
        """
            Helper method of 'getLogsWithinTimeRange' method.
        - :return: int
        """

        numberOfLines = self.tki.getModules('wc').getNumberofLines(file='/var/log/messages', rerun=True)
        if not isinstance(numberOfLines, int):
            raise Exception("Unable to get the total number of lines of the /var/log/messages")
        return numberOfLines

    def _getTimeStamp(self, results, **kwargs):
        """
            This is a method used both by 'getLogsWithinTimeRange' and 'run'. It gets the DateParseLine object for
            the '/var/log/messages' file and saves it in 'messageDate'.
        - :param results: (string/list)
        - :param kwargs:
        - :return: string or list
        """

        if not results:
            return None
        if isinstance(results, str):
            linesToParse = results.strip().splitlines()
        else:
            linesToParse = results
        try:
            for line in reversed(linesToParse):
                self.messageDate = DPL(line=line, tzdata=self.remoteTZ)
                if self.messageDate.dateStr:
                    break
            return results
        except Exception as e:
            return results

    def _getTimeWithMessageDate(self, line, **kwargs):
        """
            This is a helper method of 'getLogsWithinTimeRange' and it uses the 'parseOtherLine' method of the
            DateParseLine object if it exists. This is designed to quickly parse the date of a line in the same file
            as what the DateParseLine object is associated with. In this case that file is '/var/log/messages'.
        - :param line: string
        - :param kwargs:
        - :return: datetime object
        """

        if self.messageDate:
            return self.messageDate.parseOtherLine(line, tzinfos=self.remoteTZ)

    @staticmethod
    def _parseTimeRange(trange, targetTime):
        """
            Helper method for 'getLogsWithinTimeRange'. This parses the 'trange' parameter provided by the
            'getLogsWithinTimeRange' method.
        - :param trange: string
        - :param targetTime: datetime or DateParseLine object
        - :return: (tuple) first index is start, second index is end
        """

        trange = trange.strip().lower()
        try:
            value = int(re.findall(r'\d+', trange)[0])
            value = value / 2.0
        except:
            raise Exception("The range specified doesn't include a number value")
        if 'millisecond' in trange:
            if 'ago' in trange:
                return targetTime - timedelta(milliseconds=value * 2), targetTime
            return targetTime - timedelta(milliseconds=value), targetTime + timedelta(milliseconds=value)
        elif 'second' in trange:
            if 'ago' in trange:
                return targetTime - timedelta(seconds=value * 2), targetTime
            return targetTime - timedelta(seconds=value), targetTime + timedelta(seconds=value)
        elif 'minute' in trange:
            if 'ago' in trange:
                return targetTime - timedelta(minutes=value * 2), targetTime
            return targetTime - timedelta(minutes=value), targetTime + timedelta(minutes=value)
        elif 'hour' in trange:
            if 'ago' in trange:
                return targetTime - timedelta(hours=value * 2), targetTime
            return targetTime - timedelta(hours=value), targetTime + timedelta(hours=value)
        elif 'day' in trange:
            if 'ago' in trange:
                return targetTime - timedelta(days=value * 2), targetTime
            return targetTime - timedelta(days=value), targetTime + timedelta(days=value)

    @staticmethod
    def timeWithinSecond(targetTime, timestamp):
        """
            This uses the 'timeInRange' method to determine if a timestamp is within 1 second of the targetTime.
        - :param targetTime: (datetime) A timedelta of 1 second is used on this datetime object
        - :param timestamp: (datetime) This is passed to the timeInRange method.
        - :return: bool
        """

        if not (isinstance(targetTime, datetime) and isinstance(timestamp, datetime)):
            raise TypeError('Both targetTime and timestamp must be a datetime object')
        return messagesModule.timeInRange(start=targetTime - timedelta(seconds=1),
                                          end=targetTime + timedelta(seconds=1),
                                          timestamp=timestamp)

    @staticmethod
    def timeInRange(start, end, timestamp):
        """
            Return true if timestamp is in the range [start, end]
        """
        if start <= end:
            return start <= timestamp <= end
        else:
            return start <= timestamp or timestamp <= end
