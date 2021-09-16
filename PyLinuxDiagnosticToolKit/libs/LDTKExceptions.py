#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Tim Nodine, Ryan Henrichson

# Version: 0.1
# Date: 06-09-2016
# Description: This is a place holder for all the custom exceptions used by LDTK resources.


import traceback
import logging
from functools import wraps
from typing import Optional, Any


# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.DEBUG)
log = logging.getLogger('LDTK_Decorator')


def exceptionDecorator(returnOnExcept: Optional[Any] = None, raiseExcept: Optional[bool] = False) -> Any:
    def wrapper(func):
        """ Decorator for exception handling """
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                try:
                    args_repr = [repr(a) for a in args]
                    kwargs_repr = ["{%s}={%s}" % (k, repr(v)) for k, v in kwargs.items()]
                    signature = ", ".join(args_repr + kwargs_repr)
                    log.info(f'Calling function <{func.__name__}> with signature: {signature}')
                except:
                    log.info(f'Calling function <{func.__name__}>:')
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f'An exception occurred in {func.__name__}: {e}')
                log.debug(f'[DEBUG] exception in {func.__name__}: {traceback.format_exc()}')
                if raiseExcept:
                    if isinstance(returnOnExcept, Exception):
                        raise returnOnExcept
                    raise
                return returnOnExcept
        return wrapped
    return wrapper


class CustomException(Exception):
    """ Saves point in time exception data (use __traceback__ in python 3) """
    def __init__(self, *args, **kwargs):
        """

        :rtype: object
        """
        self.message = ""
        super(CustomException, self).__init__(*args, **kwargs)
        if isinstance(self, CommandObjectException):
            self.stack = '%s\n%s: %s' % (
                ''.join(traceback.format_stack()[:-2]).strip(), self.__class__.__name__, self.message)
        else:
            self.stack = '%s\n%s: %s' % (
                ''.join(traceback.format_stack()[:-1]).strip(), self.__class__.__name__, self.message)


# SSH Exceptions
class _errorAuth(CustomException):
    """  paramiko.AuthenticationException """
    pass


class _errorConn(CustomException):
    """  socket.error """
    pass


class _errorSSH(CustomException):
    """  paramiko.SSHException """
    pass


class _errorUnknown(CustomException):
    """  sshConnector unknown errors """
    pass


class _errorChannel(CustomException):
    """  paramkio.ChannelException """
    pass


class _becomeUser(CustomException):
    """  sshUserControl failure to become user """
    pass


class _RecvReady(CustomException):
    """  sshBufferControl failure to detect the prompt after a certain amount of time """
    pass


class _BetweenBitException(CustomException):
    """ sshBufferControl._bufferBetweenBitWait method when it takes too long to get the next bit from the buffer """
    pass


class _TimeToFirstBitException(CustomException):
    """ sshBufferControl._bufferTimeToFirstBit method when it takes too long to get the first bit from the buffer """
    pass


# Command and Command Container/Object Exceptions
class CommandObjectException(CustomException):
    """ Custom exceptions collector that outputs a single combine exception """

    baseException = None

    def __init__(self, *args, **kwargs):
        self.message = ""
        self.baseException = kwargs.pop('baseException', []) or []
        if isinstance(self.baseException, CommandObjectException) or not type(self.baseException) is list:
            self.baseException = [self.baseException.__repr__().replace(',)', ')')]
        super(CommandObjectException, self).__init__(*args)

    def appendException(self, **kwargs):
        """ Collect exceptions into a single exception object and reinitialize with new exception string message """
        if 'baseException' in kwargs:
            baseExcept = kwargs.pop('baseException', [])
            if isinstance(baseExcept, CommandObjectException) or not type(baseExcept) is list:
                baseExcept = [baseExcept.__repr__().replace(',)', ')')]
            if not self.baseException:
                self.baseException = baseExcept
            else:
                self.baseException.extend(baseExcept)
        newException = (self.message + ': ' + ', '.join([baseex for baseex in self.baseException]))
        super(CommandObjectException, self).__init__(newException)


class RequirementsException(CommandObjectException):
    pass


class PreparserException(CommandObjectException):
    pass


class ExecutionException(CommandObjectException):
    pass


class PostParserException(CommandObjectException):
    pass


class SetFailureException(CommandObjectException):
    pass


class CompletionTaskException(CommandObjectException):
    pass


class TimeoutException(CommandObjectException):
    pass


class DataFormatException(CommandObjectException):
    pass


class ForceCompleteException(CommandObjectException):
    pass
