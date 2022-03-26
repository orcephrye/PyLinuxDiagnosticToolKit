LST_LinuxDiagnosticToolKit
==========================


----
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://choosealicense.com/licenses/gpl-3.0/)
[![Docs](https://readthedocs.org/projects/ansicolortags/badge/?version=latest)](https://orcephrye.github.io/PyLinuxDiagnosticToolKit/)

Wiki can be viewed on GitHub Pages. 
URL: https://orcephrye.github.io/PyLinuxDiagnosticToolKit/

These documentation pages are made by Portray: https://timothycrosley.github.io/portray/

* REQUIRES: Python 3.7+, PyMultiprocessTools, PyCustomParsers, PyCustomCollections and Paramiko

```sh
# Install requirements (pip should point to a Python 3.7+ environment.)
pip install -r requirements.txt
```

**The Linux Diagnostic Tool Kit:**

This is a set of Modules (python packages) themed after linux commands or programs, packaged together with some tools to
interact with a remote machine. Currently, the only 'connector' is the 'sshConnector' which provides connectivity too 
Linux machines. The tools, connectors, and modules are tied together by the ToolKitInterface class in the ldtk.py 
package. 

The ToolKitInterface class should be the primary class a python script interacts with. It is as simple as importing 
the package and instantiating an object.

```pycon
from ldtk import ToolKitInterface
tki = ToolKitInterface()
```



In order to get login information the TKI uses the ArgumentWrapper package. This is a highly customizable NamespaceDict 
object. If you are not creating a callable script but utilizing this program within an environment like ipython then 
you will need too pass the ArgumentWrapper manually.
    
```python
from LST_LinuxDiagnosticToolKit.libs import ArgumentWrapper
args = ArgumentWrapper.arguments().parse_known_args()[0]
args.host = '127.0.0.1'; args.username = 'server'; args.password = 'abc123'; args.root = True; args.rootpwd = 'abc123'
tki = ToolKitInterface(arguments=args)
```

or

````python
args = ArgumentWrapper.parseString("--host 127.0.0.1 --username server --password abc123 -r --rootpwd abc123")
tki = ToolKitInterface(arguments=args)
````

    
> Note: There is a massive list of possible arguments please review the ArgumentWrapper for all possible options. Also, 
you do not necessarily need to provide it the exact class with all arguments. Simply any NamespaceDict object will do. 

For more information on Argument Wrapper please review its readme file: [tutorial](../LST_LinuxDiagnosticToolKit/ArgumentWrapper "Arguments README")

***Execute Commands:***

From here if a dev wants to run a custom command it is as simple as:

```python
cc = tki.execute("whoami")
print(cc.results)
```
    
or

```python
print(tki.execute("whoami").waitForResults())
```

Execute returns a CommandContainer if threading is True. If Threading is false then it returns the output of the
command as a string. We will get to how to use CommandContainer later.

For a full explanation go to the [CommandContainer](../LST_LinuxDiagnosticToolKit/LinuxModules/ "CommandContainer") page.

**Modules:**

Currently, there are only 'LinuxModulse' which contain 'CommandModules' and 'ProgramModules'. Eventually These will be 
reorganized once Windows is supported. 

- Command Modules are common Linux specific commands (i.e: cat, ps, etc...)
- Program Modules are programs that run on the target remote OS. (i.e: MySQL, Oracle, etc...)

To get a list of modules use the 'getAvailableModules' method. This returns a list of strings that represent the 
supported commands.

```pycon
from ldtk import ToolKitInterface
tki = ToolKitInterface()
tki.getAvailableModules()
```

Any command regardless if it is present in the list of supported modules can be executed via the 'execute' method. 
Modules are a more 'pythonic' or programmatic way of handling shell commands. They also can have special methods 
specific to the nature of the command they represent. An example of this would be 'ps' command module having a method 
'getTopCPU' or the 'll' module which has the method 'fileExist'. 

Also not all modules directly map too a single command. Some modules use multiple commands together when using a certain
methods while others are a collection of commands following a particular theme. An example of this would be the 'touch'
modules 'isWritable' method which determines if a filesystem can be written too. It also uses the 'rm' module. While
the service module combines the commands service, chkconfig, and systemctl all in one.

**The CommandModules:**

These command modules are packages that all inherit from genericCmdModule and they are themed around certain bash
commands. For example the psmodule uses the 'ps' command and has custom parsing tools to handle the output.

To use a module:

```python
ps = tki.getModule('ps')
print(ps())
print(ps(rerun=False))
print(ps(wait=10, rerun=True))
print(ps('-ef'))
print(type(ps.ef))
print(ps.getTopCPU())
```


The first command creates an instance of the psmodule and makes it aware of the ToolKitInterface.

The second command simply runs the 'ps' with default flags. Review the module itself or if in ipython simply run: 'ps?'.

All results of commands are cached. So the 'rerun' parameter is a standard option to tell the method to rerun the 
command on the remote target even if the object already has results for that command. In the case of the 'ps' command 
the rerun flag defaults too True. Most command modules the 'rerun' parameter is False.

All commands run on a spawned worker thread that represents a Paramiko SSH Channel. The parameter wait is uses to tell 
the method how long it is acceptable to wait for data back. If the command is not yet finished it doesn't stop running
the method simply returns None. If wait is None then the method will return a CommandObject if its running a new 
command or a cached results.

The arguments '-ef' are considered custom flags. The ps module will then bypass normal behavior and simply run 'ps -ef'. 
This still means the results will be cached and the standard parameters are accepted.

The method 'getTopCPU' was added to the psModule to parse the ps data in a common way. There are lots of these 'helper' 
methods across a lot of the Modules. 

> Note: Threading can be tricky and may cause unexpected behavior. For example if you run 'cat('/etc/hosts')' ten times 
in a loop it will not spin up 10 cat commands but actually just one. The default wait is 60 so it will run the first 
command to completion and then the remaining 9 will return the cache result. If you run it with 'wait=None' the cache 
process is thread safe so the CommandObject will be stored and the remaining 9 threads will simply return cached results. 
However, if you have that same loop run ten different cat commands (ie: cat /tmp/hosts, cat /etc/resolv.conf, etc...) 
commands (with wait=None) it will run all 10 in as many threads as is allowed. (default is 8) If you want to run ten of 
the same commands at the same time you will need to give each command a uniq 'commandKey' in kwargs. ie: 'commandKey=X'

**The sshConnector:**

This is more 'under the hood' stuff that is likely not necessary for most automation. The ssh Connector is a wrapper
around Paramiko and adds extra functionality to make managing users and extra channels and sftp connections.

> Getting and using a SFTP connection

```python
sftp = tki.getSFTPClient()
sftp.put('/path/too/file.out', '/remote/path/too/new/filename')
```


> Getting and using a SCP connection 

```python
scp = tki.getSCPClient()
scp.put('/path/too/file.out', '/remote/path/too/new/filename')
```


A few things to note is how to escalate too a specific user, change environment and how to make custom channels and run
commands on them.

Many methods have an optional parameter 'environment' that allows the programmer to specify a ssh channel to act on. 
By default environment=None and thus any are done to whatever SSH channel is available.

> Escalate too root (if the correct information is already passed in via arguments to the script)
    
```python
tki.becomeRoot()
tki.becomeRoot(environment=<sshEnvironment>)
```


> Escalate too root (with custom options, this also works for any other user)

```python
tki.becomeuser('root', 'abc123', loginCmd='sudo')
tki.becomeuser('root', 'abc123', loginCmd='sudo', environment=<ChannelObject>)
```


> Escalate to root before executing a command without dealing with environment directly using the standard root keyword.

```python
cc = tki.execute('whoami', root=True)
```

> NOTE: There is an argument in the ArgumentWrapper '-r' or '--root' the default is False. If passed the script will 
always automatically attempt to run the 'becomeRoot' method.

> NOTE: The TKI is aware of sudo's ability to cache creds, and is also aware of sudo requesting different passwords 
such as 'server'. When uses 'sudo' it uses 'sudo -k'. It also is aware when 'sudo' asks for the password of a different 
user. It can look at the password for the requested user. It will also attempt to retry using different methods like 
'su -' and if that failed then 'sudo su -'. This behavior is controled with the '--rootLoginExplicit' flag.

> Escalate too a different console, environment param optional

```python
tki.consoleEscalation('bash', '-norc', name='BASH')
```

> Change an environment variable, environment param optional

```python
tki.environmentChange("export=CHEESE='blah'", name='cheese')
```
    

> Creating a custom channel to then mess with.

```python
environment = tki.createEnvironment(label='cheese')
tki.becomeUser('root', 'abc123', loginCmd='sudo', environment=environment)
``` 

> Run a command on your customer channel.

```python
tki.execute('whoami', labelReq='cheese')
``` 

> Also with a commandModule

````python
print(ps(rerun=True, wait=10, labelReq='cheese'))
````

So why don't we pass the environment directly into execute or simpleExecute? Well this is because you can make multi
channels with the same label. Each with an identical environment and then run possibly 100s of commands each one finding
a thread/channel pair to execute on. 


**The CommandContainer:**

This is where a lot of the heaving lifting for command execution happens. These objects are thread safe and
customizable.

So far we have only shown what it looks like to run a single command. However, TKI can run hundreds of commands all in
specific order, all aware of each other, and all customizable in the middle of execution, while also all still being
thread safe and simple.

List/Tuples are ordered data types and imply a queue and thus commands in a list or tuple run sequentially. Dict/Set 
are unordered data types and imply a batch and run asynchronously. 

Examples:
> An Que of commands that will run one at a time.

```python
tki.execute(['whoami', 'id', 'w'])
```

> batch of commands that will run all at once.

````python
tki.execute({'whoami', 'id', 'w'})
````

> A Que of commands with custom arguments.

```python
queCmds = [{'command': 'whoami', 'commandKey': 'username', 'preparser': _someMethod},
               {'command': 'id', 'commandKey': 'userInfo', 'preparser': _someOtherMethod}]
tki.execute(queCmds)
``` 

The CommandContainer is explained in more detail in the documentation for it. In most cases you will never need its more
advanced features.

**Threading:**

The ToolKitInterface and specifically the sshConnector handles threading. This tool uses the 'threading' module within 
Python. This means it doesn't handle multipleprocess nor does it work with asyncio modules. Threading is acceptable 
because the CPU bound commands happen on a remote machine. This could technically benefit from asyncio however 
Paramiko doesn't support async as of writing this.

Below are some ways to interact with this threaded environment. 

Firstly when executing a command with the 'execute' method it will return a CommandContainer from the 
'CommandContainers' package. This is a thread safe object that acts like a task or container where the command and its
results are stored. You can string multiple commands together and wait on each of them individually or use a method 
like 'waitForIdle'. Methods that wait on threads will return a None by default implying that the thread is not yet 
finished. You can change this behavior with parameters.

```python
cmd1 = tki.execute('w')
cmd1.waitForResults(wait=10)
print(f"w output: {cmd1.results}")
```
    
or...

```python
cmd1 = tki.execute('w')
cmd2 = tki.execute('ps awux')
tki.waitForIdle(timeout=60)
print(f"W output: {cmd1.results}\nps awux output: {cmd2.results}"
```

If you are using command modules the default value for 'wait' in the parameters is 60. This means each command ran will
run one at a time finishing or at least waiting for 60 seconds before continuing to the next. 'wait' can be set to 
False or 0. That way multiple commands from the CommandModules can be ran asynchronously. Setting 'wait' too False will 
return a CC (CommandContainer) while a 0 will return a None. The CC is created but cached on the module object and can 
be retrived by running the method again.

```python
w, ps = tki.getModules('w', 'ps')
cmd1 = w('-f', wait=False)
ps(wait=None)
tki.waitForIdle(timeout=60)
print(f"W output: {cmd1.results}\nps awux output: {ps()})
```

By default the max aloud threads, and thus ssh channels for the ThreadingPool to manage is determined by the the 
'MaxSessions' variable in the '/etc/ssh/sshd_conf' configuration file on the target machine. This value is retrieved 
when the sshConnector first connects to a target box. It will default to 8 if it fails to get the value.

There is also running Ques and Batches. In this case the returning CommandContainer has a list/set of 'children' which
all have there data. A list/tuple of commands is treated as a queue of commands and thus is executed sequentially while
a Dictionary/Set of commands is treated as a batch of commands and thus are executed asynchronously.
    
This example takes roughly 15 seconds:

````python
results = tki.execute(['sleep(5); echo "one"', sleep(5); echo "two", sleep(5); echo "three"])
results.waitForResults(wait=60)
for child in results.children:
    print(child.results)
````

This example takes roughly 5 seconds:

```python
results = tki.execute({'sleep(5); echo "one"', sleep(5); echo "two", sleep(5); echo "three"})
results.waitForResults(wait=60)
for child in results.children:
    print(child.results)
```
