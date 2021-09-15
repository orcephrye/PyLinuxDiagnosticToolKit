#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: <Your Name>

# Version: v1.0
# Date: 2015
# This should be used as a template for new command modules

import logging
from LinuxModules.genericCmdModule import GenericCmdModule


# logging.basicConfig(format='%(module)s %(funcName)s %(lineno)s %(message)s', level=logging.DEBUG)
log = logging.getLogger('ModuleName')


# Default module that does nothing special. It simply wraps a Linux command into a class that is callable. It can
# support passing flags. It does nothing special formatting wise.
class ModuleName(GenericCmdModule):
    """
         <ModuleName> class. This class inherits from the GenericCmdModule. It is used to execute the Linux command
         '<ModuleName>' on remote machines.
         defaultCmd: <ModuleName>
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating <ModuleName> module.")
        super(ModuleName, self).__init__(tki=tki)
        self.defaultCmd = '<ModuleName> '
        self.defaultKey = "<ModuleName>%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ModuleName'


# Example of Control Flags that help with the way the object behaves.
class ModuleNameControlFlags(GenericCmdModule):
    """
         <ModuleNameControlFlags> class. This class inherits from the GenericCmdModule. It is used to execute the Linux
         command '<ModuleNameControlFlags>' on remote machines.
         defaultCmd: <ModuleNameControlFlags>
         defaultFlags =
    """

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating <ModuleNameControlFlags> module.")
        super(ModuleNameControlFlags, self).__init__(tki=tki)
        self.defaultCmd = '<ModuleNameControlFlags> '
        self.defaultKey = "<ModuleNameControlFlags>%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ModuleNameControlFlags'
        # Default Kwargs (Default empty) This kwargs gets merged into whatever kwargs are passed to 'run'. These kwargs
        # eventually are passed to the CommandContainer object. In the example below the root flag is passed to ensure
        # that the command ran in this module always runs on a root login. Any flag including pre/post parameters can
        # be set here.
        self.defaultKwargs = {'root': True}
        # Require flags (Default False) Some Linux commands like 'cat' for example require input or else they hang. This
        # will cause an exception to be raised if no such flag/input is provided.
        self.requireFlags = True
        # Ignore Alias (Default None) Some Linux distros and customer boxes will have aliases for commands. This flag
        # will tell the CommandContainer to attempt to ignore the alias of a command to ensure that the command you run
        # doesn't have unexpected flags.
        self.ignoreAlias = True


# import logging
# from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.PyCustomParsers.GenericParser import BashParser


# This adds support for the BashParser. BashParser is located in the PyCustomParsers package and attempts to translate
# the text output of a bash command into a indexed dataset which acts like both a Dictionary and a Set and can be
# searched similar to a relational database.
class ModuleNameBashParser(GenericCmdModule, BashParser):
    """
         <ModuleNameBashParser> class. This class inherits from the GenericCmdModule. It is used to execute the Linux
         command '<ModuleNameBashParser>' on remote machines.
         defaultCmd: <ModuleNameBashParser>
         defaultFlags =
    """

    _template = {'ColumnLabel0': 0, 'ColumnLabel1': 1, 'ColumnLabel2': 2}
    head = 1
    _header = ['ColumnLabel0', 'ColumnLabel1', 'ColumnLabel2']

    def __init__(self, tki, *args, **kwargs):
        """ This works as excepted accept it now has a new super call that specifically initializes the BashParser.
            There are several control values that needs to be passed. '_templete', 'head', '_header'. If not passed
            the bash parser will try to do its 'best guess' which uses the first line (head=0) as the template. The
            template defines the column names. While the 'header' defines the name for that column that gets printed
            when running 'formatOutput'. 'head' will specify which line to look for the headers/column names which will
            also be used in the template if the template isn't specified. Look at the psModule.py for an example.

        :param tki: (ToolKitInterface Object)
        :param args:
        :param kwargs:
        """

        log.info("Creating <ModuleNameBashParser> module.")
        super(ModuleNameBashParser, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(template=self._template, head=self.head, header=self._header)
        self.defaultCmd = '<ModuleNameBashParser> '
        self.defaultKey = "<ModuleNameBashParser>%s"
        self.defaultFlags = ""
        self.__NAME__ = 'ModuleNameBashParser'

    def run(self, flags=None, rerun=True, **kwargs):
        """ A simple wrapper for the 'run' method from GenericCmdModule. This method is called by the '__call__' method
            so this will run regardless of how the object is called.

            This method adds a '_formateOutput' meta function that simply runs 'parseInput' method from BashParser. The
            way this run method is setup is tha it will only parse the output if the default flags are used. In other
            words if the command is ran with different flags then the default flags the output will not be parsed by
            the bash parser. The idea being that flags could change the layout/format of the command output and thus
            not be parsed correctly.

        :param flags:
        :param rerun:
        :param kwargs:
        :return:
        """

        def _formatOutput(results, *args, **kwargs):
            self.parseInput(source=results, refreshData=True)
            return self

        command = {flags or self.defaultKey: self.defaultCmd + (flags or self.defaultFlags)}
        if not flags and 'postparser' not in kwargs:
            kwargs['postparser'] = _formatOutput
        return self.simpleExecute(command=command, rerun=rerun, **kwargs)

    def specialMethod(self, *args, **kwargs):
        """ This is a simple unpractical method. You can ignore the 'return' line. The point is to show case the
            '_verifyNeedForRun' method found in the GenericCmdModule. This method can take the flags from kwargs and
            look at the state of the object too see if the object needs to run before accessing data. It will run the
            default 'run' method if it thinks it needs to run. This is helpful for special parsing methods. It is also
            thread safe. So multiple threads can access different methods on the same object that each have this
            '_verifyNeedForRun' method and it will not cause the 'run' method to run more then once.

        :param args:
        :param kwargs:
        :return:
        """

        self._verifyNeedForRun(**kwargs)
        return getattr(self, 'test', None)
