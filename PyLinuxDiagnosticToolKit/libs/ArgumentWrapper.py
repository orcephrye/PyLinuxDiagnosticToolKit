#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.4
# Date: 12/10/14
# Description: This is the all in one ArgParse setup file. Note that this doesn't actually HANDLE/Parse arguments. It
# simply builds the parser. Which you can add your own custom arguments if necessary. But this ArgumentWrapper is the
# one stop shop for adding arguments that can be used by all the different facilities of the LinuxDiagnosticToolKit.
# The goal here is to place all the possible arguments into one manageable place.
# NOTE: This can take a tuple in the dest field of add_argument for compatibility purposes
# The result will be a single space joined string added as the parent attribute to the argparse namespace
# Each tuple element will be added individually to the argparse namespace as well and have the same initial value as
# the parent. These children will not be permanently synced with the parent or each other so any change to one will only
# change that one


import sys
import re
import argparse
from copy import copy
from json import loads
from PyCustomCollections import NamespaceDict
from PyCustomParsers.CustomParsers import jsonHook, literal_eval_include


# customized argument parser to allow tuples to be set in dest
# tuples are broken out into individual arguments with the same value and the tuple is removed
class ArgumentParsers(argparse.ArgumentParser):

    def __init__(self, *args, **kwargs):
        # this allows exact matching of potentially ambiguous parameter flags with case sensitive option
        self.explicitOptionMatch = kwargs.pop('explicit_option_match', None)
        # allow option strings with two prefix characters to be split on a character
        self.optionSep = kwargs.pop('option_sep', '=') or '='
        super(ArgumentParsers, self).__init__(*args, **kwargs)

    # probably do not need this override but exists to draw attention to these changes and effects
    def parse_args(self, args=None, namespace=None):
        args, argv = self.parse_known_args(args, namespace)
        return args

    # allow dest=tuple() and add each item in the tuple to the args namespace, sync values, sync keys
    # noinspection PyUnresolvedReferences,PyProtectedMember
    def parse_known_args(self, args=None, namespace=None):
        # this syncs all values across parent and child args and resets or readds the tuple keys
        def _fixerCleaner(brokenspace):
            # remove the string flags made from the original tuples
            def _cleanNamespace():
                for rspc in brokenspace:
                    if ' ' in rspc:
                        del brokenspace[rspc]
                        return _cleanNamespace()

            def _cleanActions():
                for ract in self._actions:
                    if ' ' in ract.dest:
                        self._actions.remove(ract)
                        return _cleanActions()

            def _cleanDefaults():
                for rdef in self._defaults:
                    if ' ' in rdef:
                        del self._defaults[rdef]
                        return _cleanDefaults()

            def _fixupHelper(refarg, refval):
                # set the values of all the new args to the values of the originals
                for af, av in brokenspace.items():
                    if af in refarg:
                        setattr(brokenspace, af, refval)

            # this creates a NamespaceDict isDefault on the argparse object to check default values
            # NOTE: this becomes static upon creation and does not update as arguments are changed
            def _checkDefaults():
                setattr(brokenspace, 'isDefault', NamespaceDict())
                for saction in self._actions:
                    if not brokenspace.get(saction.dest):
                        continue
                    if not saction.default or brokenspace.get(saction.dest) != saction.default:
                        brokenspace.isDefault.update({saction.dest: False})
                    else:
                        brokenspace.isDefault.update({saction.dest: True})

            # find all the new child args and sync the values with the parent then cleanup
            for argflag, argvalue in brokenspace.items():
                if argvalue and ' ' in argflag:
                    _fixupHelper(argflag.split(), argvalue)
            _cleanNamespace()
            _cleanActions()
            _cleanDefaults()
            _checkDefaults()

        # add each arg in the tuple as a new arg
        def _argattrHelper(nspace, ndest, checkaction=None):
            if not hasattr(nspace, ndest):
                if not checkaction:  # used for self._actions
                    if action.default is not argparse.SUPPRESS:
                        setattr(nspace, ndest, action.default)
                else:  # used for self._defaults
                    setattr(nspace, ndest, checkaction)

        # add the new args to the actions list
        def _actionAdder(naction, ndest):
            naction.dest = ndest
            self._actions.append(naction)

        # add the new args to the args defaults
        def _defaultAdder(ndefault, ndest):
            self._defaults[ndest] = self._defaults[ndefault]

        if args is None:
            # args default to the system args
            args = sys.argv[1:]
        else:
            # make sure that args are mutable
            args = list(args)

        # default Namespace built from parser defaults
        if namespace is None:
            namespace = NamespaceDict()

        for action in self._actions:
            if action.dest is not argparse.SUPPRESS:
                if not isinstance(action.dest, str):
                    for adest in action.dest:  # add each tuple item as new kwarg
                        _argattrHelper(namespace, adest)
                        _actionAdder(copy(action), adest)
                    action.dest = ' '.join(
                        action.dest)  # overwrite the tuple dest with the joined string so it can be referenced
                else:
                    _argattrHelper(namespace, action.dest)  # normal existing behavior

        # add any parser defaults that aren't present
        for dest in self._defaults:
            if not isinstance(dest, str):
                for ddest in dest:  # add each tuple item as new kwarg
                    _argattrHelper(namespace, ddest, self._defaults[dest])
                    _defaultAdder(dest, ddest)
                _defaultAdder(dest, ' '.join(dest))  # o/w the tuple dest with the joined str so it can be referenced
            else:
                _argattrHelper(namespace, dest, self._defaults[dest])  # normal existing behavior

        # parse the arguments and exit if there are any errors
        try:
            namespace, args = self._parse_known_args(args, namespace)
            if hasattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR):
                args.extend(getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR))
                delattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR)
            _fixerCleaner(namespace)  # ensure tuples kwargs exist again and sync all keys and values
            return namespace, args
        except argparse.ArgumentError:
            err = sys.exc_info()[1]
            self.error(str(err))

    def _get_option_tuples(self, option_string):
        result = []

        # option strings starting with two prefix characters are only
        # split at the '=' unless option_sep is specified
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if self.optionSep in option_string:
                option_prefix, explicit_arg = option_string.split(self.optionSep, 1)
            else:
                option_prefix = option_string
                explicit_arg = None
            for option_string in self._option_string_actions:
                if option_string.startswith(option_prefix):
                    if self.explicitOptionMatch:
                        if self.explicitOptionMatch is True:
                            if option_string != option_prefix:
                                continue
                        elif 'insensitive' in self.explicitOptionMatch:
                            if option_string.lower() != option_prefix.lower():
                                continue
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # single character options can be concatenated with their arguments
        # but multiple character options always have to have their argument
        # separate unless option_sep is specified
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix = option_string
            explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, short_explicit_arg
                    result.append(tup)
                elif option_string.startswith(option_prefix):
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)

        # shouldn't ever get here
        else:
            self.error(f'unexpected option string: {option_string}')

        # return the collected option tuples
        return result


# noinspection PyTypeChecker
def arguments(explicit_option_match=True, option_sep='='):
    # create argparse object to handle command line switches
    parser = ArgumentParsers(add_help=False, conflict_handler='resolve',
                             explicit_option_match=explicit_option_match, option_sep=option_sep)
    parser.add_argument('--help', action="help",
                        help="show this help message and exit")
    parser.add_argument('-v', '--verbose', dest='verbose', const=True, nargs='?', default=False,
                        help='Select verbose output that stores as True or an integer for verbosity level '
                             'and does not increase verbosity of logging')
    #
    # Arguments requested by the SSH connector
    # Username and Password may also be used for MBU for API auth in place of the standard config file
    #
    parser.add_argument('-h', '--ip', '--host', dest='host',
                        help='server hostname or ip address')
    parser.add_argument('-P', '--port', dest='port', default='22',
                        help='ssh port')
    parser.add_argument('-k', '--sshkey', '--key', dest='key', nargs='?', type=str, default="",
                        help='private ssh key')
    parser.add_argument('-u', '--username', '--user', '--uname', dest='username', default='server',
                        help='ssh login username')
    parser.add_argument('-p', '--password', '--pass', '--pasw', '--pw', dest='password',
                        help='ssh login password')
    parser.add_argument('-r', '--root', dest='root', action='store_true',
                        help='attempt root login, if root password isn\'t provided, login uses \'sudo su -\'')
    parser.add_argument('--rootpwd', dest='rootpwd', default='nopasswd',
                        help='host\'s root password, if provided login uses \'su -\'')
    parser.add_argument('--rootLogin', dest='rootLogin', default='su -', type=str,
                        help='The login command for escalating to root')
    parser.add_argument('--rootLoginExplicit', dest='rootLoginExplicit', action='store_true', default=False,
                        help='Determines if the script should retry to escalate to root with another method.')
    parser.add_argument('--bash-norc', dest='useBashnorc', action='store_true', default=True,
                        help='Determines if the script should open bash with the -norc flag to avoid custom prompts')
    parser.add_argument('--runtimeout', dest='runTimeout', type=int, default=300,
                        help='Total run time for commands (in seconds)')  # 300
    parser.add_argument('--firstBitTimeout', dest='firstBitTimeout', type=int, default=240,
                        help='The length of time to wait on the first bit of response from the target after command '
                             'execution')  # 240
    parser.add_argument('--betweenBitTimeout', dest='betweenBitTimeout', type=int, default=30,
                        help='The max length of time between two bits of data from a buffer this allowed.')  # 30
    parser.add_argument('--delay', dest='delay', type=float, default=0.01,
                        help='The length of time to wait before checking the response of a buffer')  # 0.01
    parser.add_argument('--conntimeout', dest='connTimeout', type=int, default=60,
                        help='ssh connection timeout (in seconds) review Paramiko documentation for more info')  # 60
    parser.add_argument('--iotimeout', dest='ioTimeout', type=float, default=0.2,
                        help='command timeout (in seconds), review Paramiko documentation for more info')  # 300
    parser.add_argument('--maxChannels', dest='maxChannels', type=int, default=0,
                        help='The amount of ssh channels the sshConnector can spawn. If 0 it will attempt to pull the'
                             'MaxSessions value from the target sshd_config file. This requires the root flag.')
    parser.add_argument('--proxyUser', dest='proxyUser', type=str, default="",
                        help='The proxy user for use with SSH proxy servers/bastion servers')
    parser.add_argument('--proxyServer', dest='proxyServer', type=str, default="",
                        help='The proxy device for use with SSH proxy servers/bastion servers')
    parser.add_argument('--device', '--deviceid', dest=('device', 'deviceid'), default='11111',
                        help='Device ID, used for logging')
    parser.add_argument('--devices', '--deviceids', dest=('devices', 'deviceids'), nargs='*', default=['11111'],
                        help='Use for passing multiple Device IDs')
    parser.add_argument('--retry', dest='retry', action='store_true',
                        help='Attempt to retry failed commands')
    parser.add_argument('--readonly', dest='readonly', action='store_true',
                        help='This will stop all changes that a script may cause.')
    parser.add_argument('--socks', dest='socks', action='store_true',
                        help='This tells the program to use a socket.')
    parser.add_argument('--socksp', dest='socksp', type=int, default=1080,
                        help='Tells socks to open on a custom port')
    parser.add_argument('--script', dest='scriptname', type=str, default="",
                        help='A script to call from either the Script directory or from CWD.')
    parser.add_argument('--scriptDestination', dest='destination', type=str, default="",
                        help='The destination on the target server where the file should be uploaded too. '
                             'Default is home directory')
    parser.add_argument('--parseScriptOutput', dest='parseScriptOutput', nargs='+', default=[],
                        help="Define 1 or more RBA output tag to do JSON parsing with")
    parser.add_argument('--scriptOutput', dest='scriptOutput', action='store_true',
                        help="Determine if the parsing tool will append custom output.")
    parser.add_argument('--error', '--output', '--reason', '--description',
                        dest=('error', 'output', 'reason', 'desc'), nargs='*',
                        help='The full error reason description details field from the alert in the ticket')
    parser.add_argument('--alertname', '--alert', '--alertName', dest='alert', nargs='*',
                        help='The alert name from the event')
    parser.add_argument('--account', dest='account', type=str, default="",
                        help='Account number for the server')
    parser.add_argument('--dc', '--datacenter', dest=('dc', 'datacenter'),
                        help='DC where the device resides')
    parser.add_argument('--division', dest='division',
                        help='Division for the device used a backup in case the SLA variable is not provided')
    parser.add_argument('--sku', dest='sku', type=str, default="",
                        help='Nimbus install SKU or list of all SKUs for the target device')
    parser.add_argument('--mount', dest='mount', default=None,
                        help='Mount point in alert')
    parser.add_argument('--deviceType', dest='deviceType', type=str, default='false',
                        help='Variable that provides the device type as physical or virtual')
    parser.add_argument('--osType', dest='osType', type=str, default='',
                        help='Variable that provides the OS type as Windows or Linux')
    parser.add_argument('--osVersion', dest='osVersion', type=str, default='',
                        help='Variable that provides the OS version of the OS type above')
    parser.add_argument('--os', dest='os', type=str, default='',
                        help='Variable that provides the OS')
    parser.add_argument('--source', dest='source',
                        help='This should be the monitoring source of the alert')
    parser.add_argument('--service', dest='service',
                        help='The name of the service from the event')
    parser.add_argument('--timestamp', '--timeStamp', dest='timestamp',
                        help='The timestamp of the event')
    parser.add_argument('--severity', dest='severity', default='Standard',
                        help='The severity set by the ticketing or monitoring system for the alert:\n')
    parser.add_argument('--priority', dest='priority', default='Normal',
                        help='The priority IE: (Highest,High,Normal,Low)')
    #
    # Generic API methods that may or may not be used by the modules you are using
    #
    parser.add_argument('--apiuser', '--apiUser', '--api-user', dest='apiUser',
                        help='API login username')
    parser.add_argument('--apipass', '--apiPass', '--api-pass', dest='apiPass',
                        help='API login password')
    parser.add_argument('--apitoken', '--apiToken', '--api-token', '--token', dest='apiToken',
                        help='Token to use to auth to the API')
    parser.add_argument('--api-config', '--apiconfig', '--apiConfig', dest='apiConfig',
                        help='Config file containing settings required to access and use an API')
    parser.add_argument('--api-endpoint', '--apiendpoint', '--apiEndpoint', '--endpoint', dest='apiEndpoint',
                        help='The endpoint to use for the requested API call(s)')
    parser.add_argument('--auth-endpoint', '--authendpoint', '--authEndpoint', '--api-auth', '--apiauth', '--apiAuth',
                        dest='apiAuth',
                        help='Endpoint used to auth to the requested API')
    parser.add_argument('--api-header', '--apiheader', '--apiHeader', '--header', dest='apiHeader',
                        help='Header data to be applied to API calls')
    parser.add_argument('--api-urn', '--apiurn', '--apiUrn', '--apiURN', '--api-URN', dest='urn',
                        help='Generally used for triggering RESTFul APIs')
    parser.add_argument('--method', dest='method',
                        help='Used by some API calls to force a specific call method like POST or GET')
    parser.add_argument('--postdata', '--postData', '--post-data', dest='postData',
                        help='Post data to send as the payload with the API call')
    parser.add_argument('--apitimeout', '--api-timeout', '--apiTimeout', dest='apiTimeout', default=60,
                        help='Set a custom timeout for the API call')
    parser.add_argument('--verboselog', '--vlog', dest='vlog', action='store_true',
                        help='Enable very verbose logging mostly from raw API output')
    parser.add_argument('--raise', '--exceptions', dest='makeErrors', action='store_true',
                        help='This will enable exceptions to be thrown instead of silent fails')
    parser.add_argument('--metadata', dest='metadata', type=translateMetadata,
                        help='Incoming data from an API call when a process is called')
    parser.add_argument('--index', dest='index',
                        help='Used to tell splunk where to log everything')

    return parser


def argSanitizer(theseArgs=None, parse=None, stripLines=None, dequote=None, convertEscapes=None, **kwargs):
    """
        Sanitize and parse arguments
    :param theseArgs: (list or str) args to parse
    :param parse: (bool) return argparseed args or same data structure as original theseArgs value
    :param stripLines: (bool) strip whitespace from each line but retain newlines
    :param dequote: (bool) remove excessive escapes and quoting and convert from literal whitespace
    :param convertEscapes: (bool) reduce escape characters and convert escaped characters to interpreted ones
    """
    try:
        if stripLines:
            return argLineStrip(argDequote(theseArgs))
        return argDequote(theseArgs)
    except:
        if theseArgs is None:
            theseArgs = sys.argv
    theseArgs = copy(theseArgs)
    for argIndex in range(len(theseArgs)):
        if dequote:
            theseArgs[argIndex] = argDequote(theseArgs[argIndex])
        if convertEscapes:
            theseArgs[argIndex] = argEscapeReduction(theseArgs[argIndex])
        if stripLines:
            theseArgs[argIndex] = argLineStrip(theseArgs[argIndex])
    if parse:
        return arguments(**kwargs).parse_known_args(theseArgs)[0]
    return theseArgs


# probably required due to excessive escapes from pipes.quotes which is no longer being used
# also used when multiple quotes are enclosing parameters
def argDequote(opt):  # no quotes for you
    """ Remove all quotes from around the given parameter """
    if opt.strip() and not {opt[0], opt[-1]}.difference({"'", '"'}):
        return argDequote(opt[1:-1])
    return opt


# probably required due to excessive escapes from pipes.quotes which is no longer being used
def argEscapeReduction(opt):
    """ Pair down escape characters within the given parameter """
    if r'\\' in opt:
        return argEscapeReduction(opt.replace(r'\\', '\\'))
    return argLinebreakConversion(opt.replace(r'\\', '\\'))


# probably required due to excessive escapes from pipes.quotes which is no longer being used
def argLinebreakConversion(opt):
    """ Convert literal whitespace to meaningful whitespace """
    return argQuoteConversion(opt.replace(r'\r', '\r').replace(r'\n', '\n'))


# probably required due to excessive escapes from pipes.quotes which is no longer being used
def argQuoteConversion(opt):
    """ Convert literal quotes to meaningful quotes """
    return opt.replace(r'\"', '"').replace(r"\'", "'")


# whitespace can always be a problem it seems
def argLineStrip(opt):
    """ Remove excess linebreak characters from each line if multiple lines exist """
    return '\n'.join(opt.splitlines())


def _intfloadTypeChecker(numericArg=None):
    if not numericArg:
        return numericArg
    if type(numericArg) is int or type(numericArg) is float:
        return numericArg
    if isinstance(numericArg, str):
        try:
            return re.search('\d+\.?\d*', numericArg).group()
        except:
            pass
    raise argparse.ArgumentTypeError('Float or int is required')


def parserprinter(parsedargs, valueexists=False, paramSep=None, orderList=None):
    """
        Prints the args as a string suitabe for feeding to a script
    :param parsedargs: arguments to use when creating the string
    :param valueexists: allows exclusion of args that are not something
    :param paramSep: use this instead of the default space between --param paramValue
    :param orderList: list of parameter flags w/o -- that contains the inteneded order of the parameters
    :return: string built from provided arguments
    """
    argList = []
    if paramSep is None: paramSep = ' '
    if not isinstance(parsedargs, dict):
        parsedargs = parsedargs.__dict__
    for flagargs, valueargs in parsedargs.items():
        if valueexists and not valueargs:
            continue  # skip values that do not exist if specified
        if isinstance(valueargs, list):  # nargs and such
            valueargs = '%s' % ' '.join([str(a) for a in valueargs])
        try:
            if ' ' in str(valueargs):
                valueargs = '"%s"' % valueargs
        except:
            pass
        argList.append('--%s%s%s' % (flagargs, paramSep, valueargs or ''))
    if not orderList:
        return ' '.join(argList)
    argstring = ''
    for orderedarg in orderList:
        for uarg in argList:
            if '--%s%s' % (orderedarg, paramSep) in uarg:
                argstring += uarg + ' '
    return argstring


def translateMetadata(mdata=None, _originalData=None, _secondPass=None):
    """
        Translate the metadata into a python dict object
    :param mdata: the metadata to process
    :return: the dict object
    """
    if not mdata:
        return {}
    if isinstance(mdata, str):
        if "''" in mdata:  # json object/string from 2.0
            mdata = mdata.replace("''", "'").replace("'", '"')
        try:
            ndata = loads(mdata, object_hook=jsonHook)
            if isinstance(ndata, str): raise Exception
            return ndata
        except Exception as e:
            try:
                ndata = literal_eval_include(mdata)
                if isinstance(ndata, str): raise
                return ndata
            except Exception as e:
                try:
                    ndata = dict(mdata)
                    if isinstance(ndata, str): raise
                    return ndata
                except Exception as e:
                    try:
                        ndata = loads(loads('"' + mdata + '"', object_hook=jsonHook), object_hook=jsonHook)
                        if isinstance(ndata, str): raise
                        return ndata
                    except Exception as e:
                        if not _originalData:
                            return translateMetadata(argSanitizer(theseArgs=mdata, dequote=True),
                                                     _originalData=mdata, _secondPass=True)
                        if _secondPass:
                            return translateMetadata(mdata.replace('\n', r'\n').replace('\r', r'\r'),
                                                     _originalData=_originalData)
    if _originalData:
        return _originalData
    return mdata


def metadataFromArgs(mtdata=None, inputargs=None, checkDefaults=None):
    """
        Update the metadata provided with the values from the corresponding arguments passed in
        NOTE: calling this with no parameters will cause all args to be parsed and the metadata of those args modified
    :param mtdata: the metadata dict to update
    :param inputargs: the arguments to use to update the metadata
    :param checkDefaults: check to see if the argument is set to the default value and skip if so
    :return: the modified metadata
    """
    inputargs = inputargs or _defaultArgParser() or {}
    mtdata = mtdata or inputargs.metadata or {}
    if not mtdata:
        if not inputargs:
            return dict(_defaultArgParser())
        return _defaultArgParser(inputargs)
    if isinstance(inputargs, dict):
        attrFunc = dict.get
    else:
        attrFunc = getattr
    for mtkey, mtvalue in mtdata.items():
        try:
            if checkDefaults and getattr(inputargs.isDefault, mtkey):
                continue
        except:
            pass
        mtdata[mtkey] = attrFunc(inputargs, mtkey) or mtvalue
    return mtdata


def argsBinder(bindArgsTo, argsToBind=None, overwrite=False, update=False, updateblank=False,
               excludeNoneValue=False, joinLists=False, onlyUpdateDefaults=False, excludeDefaults=False):
    """
        Bind arguments to the calling object according to filters
    :param bindArgsTo: object to bind argument to
    :param argsToBind: arguments to bind
    :param overwrite: overwrite everything on the object with the corresponding argument
    :param update: update object attributes with args if the corresponding arg is something
    :param updateblank: update only blank object attributes with corresponding args that are something
    :param excludeNoneValue: use with overwrite to prevent args with a value of None from overwriting args with a value
    :param joinLists: bool or string, string will be used as the joiner
    :param onlyUpdateDefaults: used with update to help ensure only argument values set to the default are updated
    :param excludeDefaults: prevent argument set to the default value from being bound
    :return: the modified object
    """
    return _binderHelper(bindArgsTo, argsToBind, overwrite, update, updateblank,
                         excludeNoneValue, joinLists, onlyUpdateDefaults, excludeDefaults)


def metadataToArgs(parsedArgs=None, mdata=None, overwrite=False, update=False, updateblank=False,
                   excludeNoneValue=False, joinLists=False, onlyUpdateDefaults=False):
    """
        Take the metadata passed in and apply each value to the argument list according to filters
        This does not need to apply to metadata as long as mdata and parsedArgs are dicts then
        parsedArgs will be updated with values from mdata
    :param mdata: the metadata passed in
    :param parsedArgs: usually the parsed arguments namespace but can be any object that supports setattr
    :param overwrite: overwrites all values in the args dict with those in the metadata
    :param update: update values with the same key that differ between the args and metadata
    :param updateblank: only update values in the args that are blank with the corresponding metadata
    :param excludeNoneValue: use with overwrite to prevent args with a value of None from overwriting args with a value
    :param joinLists: bool or string, string will be used as the joiner
    :param onlyUpdateDefaults: used with update to help ensure only argument values set to the default are updated
    :return: the modified object
    """
    return _binderHelper(parsedArgs, mdata, overwrite, update, updateblank,
                         excludeNoneValue, joinLists, onlyUpdateDefaults, _getMetadata=True)


def argsJoiner(parsedArgs):
    """ Convenience function to join arg lists into strings """
    return argsBinder(parsedArgs, parsedArgs, overwrite=True, joinLists=True)


# NOTE: The custom functions selected by the data type are obsolete since the custom argparse.Namespace was created
def _binderHelper(bindArgsTo=None, argsToBind=None, overwrite=False, update=False, updateblank=False,
                  excludeNoneValue=False, joinLists=False, onlyUpdateDefaults=False, excludeDefaults=False,
                  _getMetadata=False):
    def _setAttributesOn(bindArgsTo, flag, arg):
        setattr(bindArgsTo, flag, arg)

    def _setDictAttributes(bindArgsTo, flag, arg):
        bindArgsTo[flag] = arg

    def _hasAttributeDict(bindArgsTo, flag):
        return flag in bindArgsTo.keys()

    def _hasAttributeObj(bindArgsTo, flag):
        return hasattr(bindArgsTo, flag)

    def _getAttributeDict(bindArgsTo, flag):
        return bindArgsTo[flag]

    def _getAttributeObj(bindArgsTo, flag):
        return getattr(bindArgsTo, flag)

    if isinstance(bindArgsTo, dict):
        binderFunc = _setDictAttributes
        hasFunc = _hasAttributeDict
        getFunc = _getAttributeDict
    else:
        binderFunc = _setAttributesOn
        hasFunc = _hasAttributeObj
        getFunc = _getAttributeObj

    argsToBind = _defaultArgParser(argsToBind)
    if _getMetadata: argsToBind = argsToBind.get('metadata', argsToBind) or argsToBind
    for flag, arg in argsToBind.items():
        if excludeDefaults:
            try:
                if getattr(argsToBind.isDefault, flag):
                    continue
            except:
                pass
        if type(arg) is list:
            if joinLists is True:
                arg = ' '.join([str(a) for a in arg])
            elif isinstance(joinLists, str):
                arg = joinLists.join([str(a) for a in arg])
        if overwrite or not hasFunc(bindArgsTo, flag):
            if excludeNoneValue and arg is None:
                continue
            binderFunc(bindArgsTo, flag, arg)
        elif arg:
            if updateblank and not getFunc(bindArgsTo, flag):
                binderFunc(bindArgsTo, flag, arg)
            if update and arg != getFunc(bindArgsTo, flag):
                if onlyUpdateDefaults:
                    try:
                        if not getattr(bindArgsTo.isDefault, flag):
                            continue
                    except:
                        pass
                binderFunc(bindArgsTo, flag, arg)
    return bindArgsTo


# returns a dict of the parsed arguments
def _defaultArgParser(parsedArgs=None):
    if not parsedArgs:
        return arguments().parse_known_args()[0]
    try:
        return dict(parsedArgs)
    except:
        try:
            return parsedArgs.__dict__
        except:
            return parsedArgs


def parseString(string):
    """
        Takes a string or a list of strings. This is meant to be used to test scripts within ipython and the string
        value is what would normally be the arguments of a script.
    :param string: (string/list of strings)
    :return: NameSpaceDict
    """
    if type(string) is list:
        return arguments().parse_known_args(string)[0]
    if isinstance(string, str):
        return arguments().parse_known_args(string.split())[0]
    raise TypeError('This function takes only one argument a string or list of strings. Received: %s' % type(string))


class ArgumentReference(object):
    """
    Main method is argumentReference
        If getArgs is provided then get the translated parameter flags for those
        Otherwise just create a dict that will allow referencing of command line parameters by dest
    """

    argRefDict = {}
    argFuzzer = re.compile('[^\w\d_]')

    def __init__(self):
        for argparam, argvalue in arguments()._option_string_actions.items():
            if type(argvalue.dest) is tuple:
                for argvaluedest in argvalue.dest:
                    self.argRefDict[argvaluedest] = argvalue.option_strings
            else:
                self.argRefDict[argvalue.dest] = argvalue.option_strings

    def __call__(self, getArgs=None):
        return self.argumentReference(getArgs)

    def argumentReference(self, getArgs=None, tryMatch=None, argValues=None,
                          returnString=None, joinMulti=None, quoteValues=None):
        """
            Translates from dest to --param
        :param getArgs: (str, list) arguments to translate
        :param tryMatch: (bool) enables fuzzy matching of the given arg(s) to the --param name
        :param argValues: (bool) enables getting values for each argument
                          (object) provide a custom object from which to get argument values
        :param returnString: (bool) join results into a string return value
        :param joinMulti: (bool) join inner lists of parameter sets together (for backward compatibility)
        :param quoteValues: (bool) applies quoting to values if using getArgs
                            True (default): double quotes
                            False: single quotes
                            None: no quotes
        :return: (dict) getArgs not provided
                 (list) returnString not provided
                 (str) returnString is True
        """

        def _argDeduper(matchList):
            if matchList:
                for mlist in matchList:
                    if matchList.count(mlist) > 1:
                        matchList.remove(mlist)
                        return _argDeduper(matchList)
                if returnString:
                    return ' '.join([' '.join(a) for a in filter(None, matchList)])
                if joinMulti:
                    return [' '.join(a) for a in filter(None, matchList)]
                return filter(None, matchList)
            return matchList

        def _tryMatcher(baseArg, matchArg):

            def _exactMatchFilter(barg):
                return matchArg == barg.strip('-')

            def _insensitiveMatchFilter(barg):
                return matchArg.lower() == barg.strip('-').lower()

            def _fuzzyMatchFilter(barg):
                return matchArg.lower() in self.argFuzzer.sub('', barg).lower() \
                       or self.argFuzzer.sub('', barg).lower() in matchArg.lower()

            def _valueGetter(getArg):
                baseArgValue = getattr(argValues, matchArg, '')
                if not baseArgValue:  # NOTE: this will need to change if action='store_false'
                    return None
                if baseArgValue is not True:  # NOTE: this will need to change if action='store_false'
                    if quoteValues:
                        baseArgValue = '"%s"' % baseArgValue
                    elif quoteValues is False:
                        baseArgValue = "'%s'" % baseArgValue
                    for gar in reversed(range(len(getArg))):
                        try:
                            assert getArg[gar] == baseArgValue or getArg[gar + 1] == baseArgValue
                        except:
                            getArg.insert(gar + 1, baseArgValue)
                return getArg

            if tryMatch and type(baseArg) is list:
                return _valueGetter(filter(_exactMatchFilter, baseArg)
                                    or filter(_insensitiveMatchFilter, baseArg)
                                    or filter(_fuzzyMatchFilter, baseArg))
            return _valueGetter(baseArg)

        if argValues is True:
            argValues = arguments().parse_known_args()[0]

        if getArgs:
            if isinstance(getArgs, str):
                return _argDeduper([_tryMatcher(self.argRefDict.get(getArgs), getArgs)])
            return _argDeduper([_tryMatcher(self.argRefDict.get(garg), garg) for garg in getArgs])
        return self.argRefDict


if __name__ == "__main__":
    print("This file is meant to be imported")
