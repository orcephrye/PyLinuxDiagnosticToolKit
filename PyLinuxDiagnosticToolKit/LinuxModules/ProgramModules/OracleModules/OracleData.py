#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.1
# Date: 07/21/15
# Name: OracleData.py
# RSAlertOracle.sh
# This is designed to be a storage class for all the variables used by OracleLogs, OracleSystem, OracleAdrci.
# In the future if Oracle needs to become thread safe one idea would be to wrap many of these functions as properties.
# Other things that this class may do in the future is have logic for handling if some data is missing while other is
# not.


class oracleData(object):

    processMod = None
    system = None
    oracleUser = None
    suCmd = None
    suWOUserCmd = None
    adrciCmd = None
    oracleInfo = None
    oracleBase = None
    oracleCmdBase = None
    oracleHomes = None
    oracleDBs = None
    oracleLogs = None
    oracleASMLogs = None
    oraclePidToLog = None
    oracleDBToLogs = None
    oraclePMonProcesses = None
    oraMmonPids = None
    oralsofFiles = None
    oerrHome = None
    oerrInfo = None
    tnsPids = None
    lsnrctlStatus = None
    logFiles = None
    oraTrace = None
    logList = None
    logs = None
    oraError = None
    oraLogKey = None
    logFile = None
    remoteTz = None
    allLogsTooOld = None
    itemTooOld = None
    defaultFindBase = "/u01/app/oracle/diag/rdbms"
    _TNSLogCommand = 'perl -e "alarm 120; exec @ARGV" "nice -n 19 tac %s | grep -m 1 -B5 -A5 %s | tac"'

    def __init__(self, *args, **kwargs):
        super(oracleData, self).__init__(*args, **kwargs)
