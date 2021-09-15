CommandContainer
================

##Summary:
The CC is designed to make running commands within a threaded environment easier by wrapping the command and any other
functions the programmer wishes to run before/after the command has been executed into a thread safe container. The
container also can handle multiple commands and execute them in order or in parallel. 

In most cases a CommandContainer or 'CC' for short is just given a string for the 'command' parameter with the command 
too execute. To run multiple commands the 'command' parameter is either a List/Tuple or Set/Dict. A list or tuple tells
the CC that the commands provided are meant to be executed in order. While a Set/Dict tells the CC that the commands are 
meant to be executed as a 'batch' or in parallel.

In order to run other methods before and/or after the command executed the CC has additional kwarg parameters. The most
common is the preparser and postpaser. These should be either a callable object like a reference to a method/function or
a partial object from 'functools'. They can also be a list of callable objects if multiple methods need to run. As the
name suggests the preparser runs before the command is executed and the postparser runs afterward. The preparser gets 
passed the 'this' keyword argument which is a reference to the CC object itself. While the postparser and all other 
methods that run after command execution get both the 'result' keyword and 'this'. 

If a CC is given one of these keyword arguments it will attempt to run this function when appropriate. Other functions
are requirements, onComplete, onFail. The order of execution is: requirements, preparsers, execute command, postparsers,
then either onComplete or onFail. onFail may run at any point of failure. 

The point of this is too allow these methods to run along with the thread that is handling the command in a safe way 
that allows the developer to simply wait on the CC for the finial results. It can also be used to create some rather 
complex execution paths that can be reduced down to just simple YAML/Json.  


## In depth review
### Definitions:
* **wait**: The length of time to wait for a command container to complete.

* **timeout**: Same as wait except that an exception will be raised if exceeded.
    
* **delay**: The length of time between each action in a collection (delay between each retry)

### Structure
There are 5 main classes that make up a CommandObject. The classes are divided based on purpose: 
> **Data**, **Parsers**, **Requirements**, **Setup**, **Logic**
  
Each of these inherits the one before it in the following order:
> **CommandData**, **CommandParsers**, **CommandRequirements**, **CommandSetup**, **CommandContainer**

* CommandData:
> As its name implies it has all the data things.
  It contains basic data and attribute modifiers for use under the hood.

* CommandParsers:
> This parses and houses the command and commandKey for the CommandObject.
  This is another class that operates under the hood when the CommandObject is created.

* CommandRequirements:
> This auxiliary workhorse handles parsing and running of command requirements using threading.
    Parsing occurs during instantiation and running of requirements happens near the start of main execution.

* CommandSetup:
> This handles the custom methods and sets them on the CommandObject during instantiation.
    This also handles the most basic checks to ensure the acceptable state of the CommandObject before main execution.
    Execution of the preparser(s) also happens here.
    This class is a little odd since the checks run before requirements and the preparser runs immediately afterward.

* CommandObject:
> The workhorse that runs the execution portions of CommandRequirements and CommandSetup as well all commands.
    This contains most of the logic that manipulates data and calls custom parsing.

## Execution of Commands

### A single Command 
A single command is simple enough:

The CommandData gets the command through the positional argument(s) 'command' and/or 'commandKey'. These are wrapped 
into properties and are parsed by the private methods _parseCommand and _parseCommandInput. The commandKey (the second
positional argument) is designed to be a way to identify the CommandObject. If the CommandContainer is not provided 
with a commandKey it attempts to derive it from the command itself.

* **NOTE**: The 'command' positional argument can be many different data types, and this is what determines behavior. If
it's a string then it assumes it's a command to run. If it's a single length item (len(item) == 1) then it pulls that
item, assuming it's a command to run. An example of this would be a list with a single item, or a dict, or whatever 
data type with just one entry. Other data types will be explained later.


CommandData sets up other variables. CommandRequirements parses the requirements and prepares them for execution. 
CommandSetup configures any custom methods on the CommandObject. Now the CommandObject is finished and it is ready for
execution.

Executing a CommandObject requires adding it to the sshThreader. Eventually it will be pulled by a Thread and passed to 
the _exeThread method within sshThreader. The _exeThread function's job is to safely call the CO's method 'executor' and
pass it all the finial parameters necessary for the CO to run correctly.
    
The 'executor' method first runs the setup method from CommandSetup to finish CO configuration using the parameters 
passed to it by _exeThread. Then it checks for requirements to run before the command, kicks off a thread for each, and 
waits for completion. After requirements the CommandObject runs preparser(s) to perform the final command 
preconfiguration.
    
It then sends the command to a threaded channel or the main thread for execution. Once execution completes, it kicks off
the default parser and any customer parsers. Lastly it runs the completion task(s).

Once the thread is done, the 'with' statement inside the '_exeThread' exits the CommandObject, and finalizes the 
completion of the CommandObject.

1) CommandObject (CO) is created with the command(s) and other options.
2) A 'with' is used on the CO in a thread.
3) _exeThread() calls executor() and passes final setup parameters.
4) executor() checks to make sure the CO is ready for execution.
5) executor() completes the setup of the CO.
6) The setup routine check to ensure the CommandObject can be run.
7) Requirements are run if applicable.
8) The preparsers are run if applicable.
9) executor() passes the command string to be executed based on parameters provided at CO's creation.
10) Postparsers are run if applicable.
11) The completion task is run if applicable.
11) In the event of a failure setFailure() is kicked off, otherwise executor() completes finally.
12) _exeThread() now exists the 'with' statement on the CO back in step 2.
13) Exiting the with statement completes the process.

### Multi Commands
Ok, so this is where data types get really tricky. Depending on the data type and how it is formatted will determine if 
the CommandObject kicks off children, and also in what order those children are run.

Any data type that is ordered implies that the commands within that data type run in that order sequentially, for 
example, list, tuple, or OrderedDict.

Any data type that is unordered implies that the commands within that data type run in parallel in whatever order the 
threads happen to execute them; examples are set, dict.

You can compound commands within this data structure. Basically, you can layer this to your hearts content. All the 
commands are linked to each other through their parents. Parents keep track of their children so that children can 
become aware of each other and their state, including whether they have finished executing or not and what their results
are.

This allows you to piercingly control the order of operations of commands, and gives you the ability to execute commands
in queues, ensuring that each finish before the other, while at the same time asynchronously other commands are 
executing and acting on each other.

Now, if you want to pass custom arguments instead of just the 'command' argument, that is where dicts come in. Dicts can
be passed in as **kwargs, and any item in a list or set can be a dict. If it is, the CommandObject will create a new 
CommandObject by simply saying CommandObject(**item). This allows you to create extremely controlled AND customized 
executions of commands.

* A helpful hint: In the repo 'PyCustomCollections' there is a Python Package called 'CustomDataStructures' that 
contains a class called 'FrozenDict'. This is an immutable hashable dictionary, meaning that you can use it within a 
set. This can be helpful if you have a set of 10 commands, but you only want to customize 1 or 2 of them. Normally you
would have to make the set a dictionary of dictionaries, but with a FrozenDict, you can just change the necessary items 
in the set.


There is a lot more going on, but that is the basics. The CommandObject/CommandContainer can be as simple as passing 
'whoami', or as complicated as passing 150 commands that all need to run in a specific order and relay data to each
other.

Most of the time you will not to need directly touch the CO. You will use the 'execute' or 'simpleExecute' functions.
The 'execute' method is located within the 'ldtk.py', and 'simpleExecute' within the 'genericCmdModule.py'.


Bread and butter routines used exclusively by the executor method
* NOTE on setLastResults: This is the facilitator method and tracks stuff when it gets data.
    Tracks the overall timeout for the CommandObject and raises an exception when exceeded
    Tracks and sets lastResults for both parents and children recursively
    Checks for failures and stopOnFailure and calls the setFailure method
    Returns False when a failure is detected and True otherwise

* NOTE on finalizeExecution: This runs tasks after execution and finalizes the results for the CommandObject.
    Tracks failures and when to stop with stopOnFailure
    Fully executes postparsers and the completion task

## Control Methods

Control methods (passed through kwargs and must accept args and kwargs):
    
* preparser:
>    A function or list of functions to preparse the command before running it.
    Passed the command object as this=self so has access to and can manipulate all elements of the object.
    Does not need to return anything and results will not be checked.
    Changes to the command object must be done directly on the object passed to it (this).
    Failure is recognized by:
        raising or returning an exception
    Failure will stop the process before requirements are run.
* requirements:
>    A dictionary of functions that are required to run and succeed before any commands or children.
    The values can also be an indexed iterable (list, tuple) of length 2 with:
        The first value as the function to be run as the requirement.
        **[3]** The second value will be the condition used to check the results for success or failure.
        **[4]** This can be any value checked == results or a function that must raise or return an exception.
            Anything other than an exception raised or returned from the function will be considered a success.
    Run threaded and passed wait, timeoutExceptions, outputChecker, and kwargs.
    Failure is recognized by:
        checking results for an instance of Exception
        checking results == failure condition (defaults to None **[1]** for timeout)
        checking result of failureCondition(results) for an instance of Exception
        raising or returning an exception
    Failure condition can be set and defaults to None **[1]**, or an exception can be raised or returned.
    Failure will stop the process before any commands are run.
* postparser:
>    Can be a function or list of postparser functions that decide if the command(s) succeeded.
    Results of this/these function(s) replace the command(s) results.
    Passed the command or children results, the command object as this=self, and kwargs.
    Failure is recognized by:
        raising or returning an exception
    Failure does not stop the process.
* completiontask:
>    A function to be run after all other tasks before exiting the command object.
    Passed command results, command object as this=self, kwargs, so can modify the object if needed.
    Can be skipped if stopOnComplete is set and a failure has been recognized.
    Failure is recognized by:
        raising or returning an exception
    Results of this task do not directly affect the overall results.
* onFail:
>    A custom function to define the behavior and results of the command object if a failure is recognized.
    Passed the command results, the command object as this=self, and kwargs.
    Results of this function replace the results of the command object.
    Failure is recognized by:
        raising or returning an exception

## Control flags:
* noParsing:
>    Do not create the command tags for output and do not parse the results as a string.
    This will still attempt to remove the command tags in case they are present.
* stopOnFailure:
>    Causes ordered commands to stop execution if a member of the queue fails, halting further execution.
    Also allows exceptions to be returned from batch execution if a command fails.
* timeoutExceptions **[2]**:
>    Causes exceptions to be returned instead of None in the event that a piece of the process times out.
    Normally a result of None is the only indicator that a command or function has not completed.
* requirementsCondition:
>    This can be set to any value or function and will be used to verify if the requirements succeeded.
    This is a global condition for all requirements and is only used if provided.
    Specific conditions for individual requirements **[3]** will override this.
    This is used in the same way as the failure conditions for individual requirements **[4]**.

**[1]** The default exists to track timeouts.

**[2]** Existence of this is questionable and may be removed at some point.

**[2]** Update the timeouts/waits/delays and so on.
