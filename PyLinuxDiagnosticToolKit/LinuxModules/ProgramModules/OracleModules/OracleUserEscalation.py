#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.1
# Date: 1/05/16
# Name: OracleUserEscalation.py
# RSAlertOracle.sh
#


import logging
from functools import partial


log = logging.getLogger('OracleUserEscalation')


class OracleEscalation(object):

    def __init__(self, *args, **kwargs):
        log.debug(" === Creating Oracle Escalation Module")
        super(OracleEscalation, self).__init__(*args, **kwargs)

    @staticmethod
    def checkUserExists(**kwargs):
        try:
            return kwargs.get('this').tki.modules.id(kwargs.get('username'), wait=30) is not False
        except Exception:
            return False

    @staticmethod
    def buildKwargs(**kwargs):
        username = kwargs.get('username', '')
        dbname = kwargs.get('dbname', None)
        oraclehome = kwargs.get('oraclehome', '')
        sqlplus = kwargs.get('sqlplus', False)
        resetConsole = kwargs.get('resetConsole', True)

        # Setting up the requirements
        req = partial(OracleEscalation.checkUserExists, **{'username': username})
        if 'requirements' in kwargs:
            kwargs['requirements'].update({'userExists': req})
        else:
            kwargs['requirements'] = {'userExists': req}

        # Setting up the preparser
        preparser = []
        if username:
            preparser.append(partial(OracleEscalation.escalateOracleUser, **{'oracleuser': username}))
        if dbname:
            preparser.append(partial(OracleEscalation.escalateEnv, **{'dbname': dbname, 'oraclehome': oraclehome}))
        if sqlplus:
            preparser.append(partial(OracleEscalation.escalateToSQL))
            kwargs['noParsing'] = True

        if 'preparser' in kwargs:
            if type(kwargs['preparser']) is list:
                kwargs['preparser'].extend(preparser)
            else:
                preparser.append(kwargs['preparser'])
                kwargs['preparser'] = preparser
        else:
            kwargs['preparser'] = preparser

        # Setting up the completion task
        if 'completiontask' not in kwargs and resetConsole:
            completiontask = None
            if sqlplus:
                completiontask = OracleEscalation.resetEnvironmentObject
            elif username:
                completiontask = OracleEscalation.deescalateOracleUser
            kwargs['completiontask'] = completiontask
        return kwargs

    @staticmethod
    def escalateOracleUser(*args, **kwargs):
        oracleUser = kwargs.get('oracleuser', 'oracle')
        this = kwargs.get('this')
        if not this.requirementResults:
            return False
        elif not this.requirementResults.get('userExists'):
            log.debug(" === Oracle user: %s appears to not exist. The results are: %s" %
                      (oracleUser, this.requirementResults.get('userExists')))
            return False
        cO = this.EnvironmentObject
        log.debug("Environment ID: %s UserList: %s The Console is: %s" % (cO.EnvironmentID, cO.userList, cO.console))
        if cO.userName == oracleUser:
            return True
        else:
            if cO.becomeRoot():
                return cO.escalate(loginCmd='su -', userName=oracleUser)
            log.info("Failed to become root! Returning false.")
            return False

    @staticmethod
    def escalateEnv(*args, **kwargs):

        this = kwargs.get('this', None) or None
        dbname = kwargs.get('dbname', '')
        oracleHome = '/' + kwargs.get('oraclehome', '').strip().strip('/')

        def _handleOraenv(sshB, cmd, sid, environment, userName, out, console):
            if 'ORACLE_SID = ' not in out.getvalue().splitlines()[-1]:
                return False
            sshB._bufferControl(environment, sid, out, unsafe=True)
            output = out.getvalue().splitlines()[-1]
            if 'ORACLE_HOME =' in output:
                sshB._bufferControl(environment, oracleHome, out, unsafe=True)

        this.EnvironmentObject.escalate(escalationCmd='. oraenv', escalationArgs="", escalationInput=dbname,
                                        name=dbname, env=True, escalationHook=_handleOraenv, prompt='ORACLE_SID = ')

        output = this.EnvironmentObject.executeOnEnvironment('echo $ORACLE_SID')

        if dbname in output:
            return True
        elif dbname not in output and oracleHome:
            exportCmd = 'export ORACLE_SID=%s; export ORACLE_HOME=%s; ' \
                        'export PATH=%s/bin:$PATH; export LD_LIBARY_PATH=%s/lib' \
                        % (dbname, oracleHome, oracleHome, oracleHome)
            this.EnvironmentObject.executeOnEnvironment(exportCmd)
            return True
        return False

    @staticmethod
    def escalateToSQL(*args, **kwargs):
        this = kwargs.get('this', None) or None
        return this.EnvironmentObject.escalate(escalationCmd='sqlplus / as sysdba', escalationArgs="",
                                              console=True, name='sqlplus', prompt='SQL>')

    @staticmethod
    def deescalateOracleUser(*args, **kwargs):
        kwargs.get('this').EnvironmentObject.becomeRoot()

    @staticmethod
    def logOutSQL(*args, **kwargs):
        kwargs.get('this').EnvironmentObject.logoutConsole()

    @staticmethod
    def resetEnvironmentObject(*args, **kwargs):
        OracleEscalation.logOutSQL(*args, **kwargs)
        OracleEscalation.deescalateOracleUser(*args, **kwargs)

    @staticmethod
    def parsePost(newPostParser, insert=True, **kwargs):
        if 'postparser' not in kwargs:
            kwargs['postparser'] = newPostParser
        elif type(kwargs['postparser']) is list:
            newPostParser = [newPostParser]
            if insert:
                newPostParser.extend(kwargs['postparser'])
                kwargs['postparser'] = kwargs['postparser']
            else:
                kwargs['postparser'].extend(newPostParser)
        else:
            newPostParser = [newPostParser]
            if insert:
                newPostParser.append(kwargs['postparser'])
                kwargs['postparser'] = newPostParser
            else:
                newPostParser.insert(0, kwargs['postparser'])
                kwargs['postparser'] = newPostParser
        return kwargs
