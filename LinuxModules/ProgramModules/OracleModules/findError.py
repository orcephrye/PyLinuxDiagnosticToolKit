#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 1.7
# Date: 10-23-14
# Name: findError.py
# findError.py
# Find the Oracle error in the Oracle log and gets the 5 lines before and after it


import re
import logging
import pytz
import pytz.reference
from PyCustomCollections.PyCustomCollections.CustomDataStructures import IndexList
from PyCustomParsers.PyCustomParsers.dateparseline import DateParseLine


log = logging.getLogger('Find Error')


class SearchLog(object):

    # Below are the starting variables. After init this data is deleted by python to conserve space
    source = None
    sourceDict = None
    localTz = None
    remoteTz = None

    # These are variables that are used to help find the data in question.
    timeReList = None
    ageLimit = None
    OLD = None
    itemOLD = None
    before = None
    after = None

    # These are locations that store data about the search results.
    searchDict = None
    searchDictKey = None
    searchCode = None
    searchPos = None
    searchDate = None

    # These are the primary variables of concern. These are the variables that you are more likely to be working with.
    searchItem = None
    searchLog = None
    searchDateLog = None

    def __init__(self, source, searchCode, timeReList=None, ageLimit=3, before=5, after=5, remoteTz=None, **kwargs):
        """
            Here is where the code actually runs.
        :param source: This can either be a str or a list. It is passed to the 'setSource' function to attempt to parse
            the data into a format that the rest of the code can use.
        :param searchCode: This is the 'code' or 'string' that this program will attempt to find.
        :param timeReList: This has to be a list. It should be a list of 'strings' that are regexs.
        :param ageLimit: This has to be an int. And the number repersents the number of days old a timestamp can be.
        :return: A class object.
        """
        log.debug(" === Creating the SearchLog Module!")
        self.setSource(source=source)
        if type(remoteTz) == str:
            try:
                log.debug("The remoteTz is: %s" % remoteTz)
                self.remoteTz = pytz.timezone(remoteTz)
            except Exception as e:
                log.debug("There was a failure to convert the string into a timezone:\n%s" % e)
        else:
            self.remoteTz = remoteTz
        self.localTz = pytz.reference.LocalTimezone()
        if type(searchCode) is not list:
            if type(searchCode) is str:
                self.searchCode = searchCode.split()
            else:
                self.searchCode = [searchCode]
        else:
            self.searchCode = searchCode
        if timeReList:
            if type(timeReList) == list:
                self.timeReList = timeReList
            else:
                self.timeReList = list(timeReList)
        self.before = before
        self.after = after
        self.ageLimit = ageLimit
        self.initiateWork()

    def initiateWork(self):
        if self.filterLogs():
            self.OLD = False
            log.debug("Some logs are not too old to be searched")
        else:
            self.OLD = True
            log.debug("All logs are too old to be searched.")
        if self.source:
            del self.source
        if not self.sourceDict:
            log.debug("There is no sourceDict exiting")
            return
        log.debug("Preforming search!")
        logKey = self._preformSearch()
        if logKey:
            self.searchDictKey = logKey
        return

    def garbageCollection(self):
        if self.searchDict:
            del self.searchDict
        if self.searchCode:
            del self.searchCode
        if self.searchPos:
            del self.searchPos
        if self.searchDate:
            del self.searchDate
        return

    def setSource(self, source):
        if not self._parseSource(source=source):
                raise Exception("Failed to parse source")

    def filterLogs(self):
        """
            The purpose of this function is to take the data from source and remove old logs. The logs that are still
            young are moved to sourceDict and the key is the date of the latest entry that has a timestamp.
        :return: logs dict
        """
        if not self.source:
            return None
        logs = self.source
        logs = self._removeOldLogs(logs, self.ageLimit, self.timeReList)
        if not logs:
            return None
        self.sourceDict = logs
        return logs

    def search(self, logItem):
        """
            Search a single log that is passed too it.
        :param logItem: A single log to search through
        :return:
        """
        log.debug("The searchCode is: %s" % self.searchCode)
        if not self.searchCode:
            return None
        if type(logItem) is not IndexList:
            IndexLog = self._createIndex(logs=logItem)
        else:
            IndexLog = logItem

        def cmpSortFunc(x, y):
            return IndexLog.index(x) - IndexLog.index(y)

        errorLines = IndexLog.getSearch(*self.searchCode)
        # log.debug("The errorLines are: %s" % errorLines)

        if not errorLines:
            return None
        sortedErrorLines = sorted(errorLines, cmp=cmpSortFunc)
        self.searchItem = sortedErrorLines[-1]
        logItem.reverse()
        self.searchPos = len(logItem) - logItem.index(self.searchItem) - 1
        logItem.reverse()
        self.searchLog = self._getRange(IndexLog, self.searchPos, before=self.before, after=self.after)
        tempDate = self._getTime(self.searchItem, self.searchLog, self.timeReList, remoteTz=self.remoteTz)
        if tempDate and tempDate.dateTime:
            log.debug("It appears that the searchItem has a timestamp: %s" % tempDate)
            self.searchDate = tempDate

        return IndexLog

    def getSearchDateInfo(self, indexedLog):
        """
            Builds the searchDateLog information. Tries to do this by either using Correlation from IndexList if it
            has the searchDate. Or we search the logs from the searchPos backwards and forwards for the first
            occupancies of a timestamp.
        :param logKey:
        :return:
        """
        if self.searchDate:
            log.debug("SearchDate is already set: %s" % self.searchDate)
            self.searchDateLog = self._searchItemDate(indexedLog, self.searchDate)
        else:
            self.searchDateLog = self._getLogsWithinRange(indexedLog, self.searchPos,
                                                          self.timeReList, remoteTz=self.remoteTz)
            if self.searchDateLog:
                self.searchDate = self._getTime(self.searchDateLog[0], self.timeReList, remoteTz=self.remoteTz)
                log.debug("SearchDate is now set too: %s" % self.searchDate)

    @staticmethod
    def covertToString(logline, boldLine=None):
        output = ""
        for item in logline:
            tempLine = ' '.join(item)
            if boldLine and boldLine in tempLine:
                if tempLine.count('[') == tempLine.count(']'):
                    tempLine = "[b]" + tempLine + "[/b]\n"
            else:
                tempLine += "\n"
            output += tempLine
        return output

    # Private Functions
    def _preformSearch(self):
        if not self.sourceDict:
            return None
        self.itemOLD = False
        logKey = self._getOldestLog(self.sourceDict)
        # log.debug("Got the logKey '%s' for the oldest Log. Now running search on log!" % logKey)
        IndexLog = self.search(logItem=self.sourceDict[logKey])
        if IndexLog:
            self.getSearchDateInfo(indexedLog=IndexLog)
        if not IndexLog:
            # log.debug("The IndexLog is empty. Searching for the next entry")
            self.sourceDict.pop(logKey)
            return self._preformSearch()
        elif self._isTooOld(self.searchDate, ageLimit=self.ageLimit):
            # log.debug("The IndexLog is too Old. Searching for the next entry")
            self.itemOLD = True
            self.sourceDict.pop(logKey)
            return self._preformSearch()
        else:
            # log.debug("The entry is not too old. Making the searchDict.")
            self.searchDict = {logKey: IndexLog}
        return logKey

    def _removeOldLogs(self, logs, ageLimit, timeReList=None):
        output = {}
        for logItem in logs:
            for row in reversed(logItem):
                # log.debug("The row is: %s" % row)
                logTime = self._getTime(line=row, timeReList=timeReList, remoteTz=self.remoteTz)
                if logTime and logTime.dateTime:
                    # log.debug("The date found in the row is: %s" % logTime.dateTime)
                    if not self._isTooOld(logTime, ageLimit):
                        output[logTime] = logItem
                    break
        return output

    # noinspection PyUnresolvedReferences
    def _parseSource(self, source=None):
        newSource = []
        if not source:
            source = self.source
        if not source:
            return False
        if type(source) is str:
            newSource.append([row.split() for row in source.splitlines()])
        elif type(source) is dict:
            newSource = self._parseSource(source.values())
        elif type(source) is list:
            if len(source) >= 1 and type(source[0]) is list:
                if len(source[0]) >= 1 and type(source[0][0]) is str:
                    self.source = source
                    return source
                else:
                    return []
            elif len(source) >= 1 and type(source[0]) is str:
                for logItem in source:
                    newSource.append([row.split() for row in logItem.splitlines()])
            else:
                return []
        else:
            return []
        self.source = newSource
        return self.source

    def _addTzTooDate(self, dateObject):
        if type(dateObject) == DateParseLine:
            dateObject.dateTime = DateParseLine.dateTime.replace(tzinfo=self.remoteTz)
            return dateObject
        return dateObject.replace(tzinfo=self.remoteTz)

    def _isTooOld(self, dateObject, ageLimit):
        return DateParseLine.inPast(dateObject, threshold=ageLimit, tzinfos=self.localTz)

    @staticmethod
    def _searchItemDate(IndexedLog, searchDate):
        timeSearch = searchDate.getDateString().split()
        searchDateLog = IndexedLog.getCorrelation(*timeSearch)
        if searchDateLog:
            searchDateLog = SearchLog._createIndex(searchDateLog)
        return searchDateLog

    @staticmethod
    def _getLogsWithinRange(logs, pos, timeReList=None, remoteTz=None):
        logLength = len(logs) - 1
        for before in reversed(range(0, (pos + 1))):
            tmpDp = SearchLog._getTime(line=logs[before], timeReList=timeReList, remoteTz=remoteTz)
            if tmpDp and tmpDp.dateTime:
                break
        for after in range(pos, (logLength + 1)):
            tmpDp = SearchLog._getTime(line=logs[after], timeReList=timeReList, remoteTz=remoteTz)
            if tmpDp and tmpDp.dateTime:
                break
        # log.debug("\n\n\nHere is the pos: %s\nHere is before: %s\nHere is after: %s\n\n\n" % (pos, before, after))
        if before == 0 and after > logLength:
            return None
        if after == logLength:
            return logs[before:]
        return logs[before:after]

    @staticmethod
    def _getRange(IndexSource, pos, before, after):
        IndexSourceLength = len(IndexSource) - 1
        if (pos + after) >= IndexSourceLength:
            after = pos + after - ((pos + after) - IndexSourceLength)
        else:
            after = (pos + after) - IndexSourceLength
        if (pos - before) < 0:
            before = pos - (before - abs(pos - before))
        else:
            before = (pos - before)
        if after == IndexSourceLength:
            return IndexSource[before:]
        else:
            return IndexSource[before:after]

    @staticmethod
    def _getTime(line, lines=None, timeReList=None, remoteTz=None):
        def pullDatePosList(dateObj):
            if len(dateObj.posList) > 0:
                return dateObj.posList[0]
            return 100

        def filterDateList(dateObj):
            if dateObj.dateStr:
                return dateObj
            return None

        if timeReList:
            for timeRe in timeReList:
                m = re.search(timeRe, ' '.join(line))
                if m:
                    return DateParseLine(m.group().strip(), tzdata=remoteTz)
        else:
            tempDateList = [DateParseLine(line, tzdata=remoteTz)]
            if lines:
                for lineItem in reversed(lines[0:lines.index(line)]):
                    tempDateList.append(DateParseLine(lineItem, tzdata=remoteTz))
            tempDateList = filter(filterDateList, tempDateList)
            if tempDateList:
                return min(tempDateList, key=pullDatePosList)
        return None

    @staticmethod
    def _getOldestLog(logs):
        return max(list(logs))

    @staticmethod
    def _createIndex(logs):
        IndexSource = IndexList()
        map(IndexSource.append, logs)
        return IndexSource
