A short introduction. This tutorial is meant to run in ipython in a directory that has both the 
PyLinuxDiagnosticToolkit (probably development branch) and other Py* packages from my repo. 

This goes over some useful abilities of the LDTK and how to use them.

Step 1) Imports:
```python
import PyMultiprocessTools; import PyCustomCollections; import PyLinuxDiagnosticToolKit; import PyLinuxDiagnosticToolkit; from ldtk import ToolKitInterface
%pycat PyLinuxDiagnosticToolkit/__init__.py
```

> Notes: Explain that when you import a package from any Py* package and PyLinuxDiagnosticToolkit the __init__ file 
imports all other directories into the namespace.

Step 2) ArgumentWrapper:

```python
import ArgumentWrapper; args = ArgumentWrapper.arguments().parse_args(); args.host = "127.0.0.1"; args.password = ""; args.username = "rye"; args.rootpwd = ""
args
tki = ToolKitInterface(arguments=args)
```


> Notes: ToolKitInterface uses argparse or rather our own version of it. Normally scripts are executed with arguments 
just like any other shell command. However, when using ipython to test code you will have to set the flags manually 
as demonstrated above.

Step 3) Load modules:

```python
cat = tki.getModules('cat')
cat.__str__
cat, ps, kill = tki.getModules('cat', 'ps', 'kill')
cat.__str__
tki.modules.cat.__str__
```


> Notes: Show off how to pull in different modules. Show off how the tki knows what modules are loaded and not so that 
it will not reload modules. There is only one of each module. 

Step 4) Use Modules:

```python
filename = '/Path/too/a/simple/file.txt'
cat = tki.modules.cat
cat?
%time cat(filename)
%time cat(filename)
%time cat(filename, rerun=True)
type(cat.catPathtooasimplefiletxt)
print(cat.catPathtooasimplefiletxt.results)
```


> Notes: Show that the first command you run requires logging into a shell first. Shows how a module saves the output 
of commands and how to rerun commands. Also show how it saves output by binding it to the module. 

Step 5) More using modules:
(You will need to replace 'rye' with a user on the machine you are SSH'ed into)
(You may need to replace 'firefox' with 'chrome' or the name of some other programming running on the machine ou are SSH'ed into)

```python
ps = tki.modules.ps
ps?
%pycat PyLinuxDiagnosticToolkit/LinuxModules/CommandModules/processModules/psmodule.py
%time ps()
ps[0]
ps['PID']
ps[('USER', 'rye')]
print(ps.formatLines(ps[('USER', 'rye')]))
ps.findProcess('firefox')
ps.findProcess('firefox')['PID']
print(ps.formatLines(ps.findProcess('firefox')))
print(ps.getRunQue())
print(ps('-ef'))
```

> Notes: Shows how a module can be a callable object that also can have methods that act upon the data from the default 
command. Also how that data is stored in a database like object that also is printable. This also shows how this may 
work with other modules. 

Step 6) SFTP file upload:
(NOTE: You will need to make a simple text BASH script ie: echo -e '#!/bin/bash\necho "cheese"' >> testScript.sh and then you will need too
make a tar ball with it via: tar czvf testScript.tar.gz testScript.tar.gz )

```python
tki.putSFTP?
tki.putSFTP('~/testScript.tar.gz', '/tmp/testScript.tar.gz')
tar = tki.getModules('tar')
tar('xvfz /tmp/testScript.tar.gz -C /tmp/')
print(tki.execute('bash /tmp/testScript.sh').waitForResults(wait=10))
```

> Notes: This is pretty simple. It is an example of how to use the tki to upload a tar ball and then remotely unzip it 
and execute the bash script on the remote machine.

Step 7) Running commands without modules and special flags:

```python
    cmdObj = tki.execute('w')
    print(cmdObj.waitForResults(wait=10))
    
    print(tki.execute('touch /etc/os-release').waitForResults(wait=60))
    
    def testRequirement(*args, **kwargs):
        cmdObj = tki.execute('which touch')
        cmdObj.waitForResults(wait=60)
        print(f"Is touch command installed?: {cmdObj.results}")
        if '/touch' in cmdObj.results:
            return cmdObj.results
        raise Exception('could not find touch cmd!')
        
    print(tki.execute('touch /etc/os-release', requirements={'testReq': testRequirement}).waitForResults(wait=60))

    def testPreparser(*args, **kwargs):
        this = kwargs.get("this")
        print(f"The kwarg this type is: {type(this)}")
        if not this.requirementResults:
            return False
        print(f"The results of the requirements are: {this.requirementResults}")
        this.command %= str(this.requirementResults.get('testReq', ''))
        return True
        
    print(tki.execute('%s /etc/os-release', requirements={'testReq': testRequirement}, preparser=testPreparser).waitForResults(wait=60))
    print(tki.execute('%s /etc/os-release; echo $?', requirements={'testReq': testRequirement}, preparser=testPreparser).waitForResults(wait=60))

    def testPostpaser(results, *args, **kwargs):
        if '0' == results:
            return True
        return False
        
    print(tki.execute('%s /etc/os-release; echo $?', requirements={'testReq': testRequirement}, preparser=testPreparser, postparser=testPostpaser).waitForResults(wait=60))
    tki.getHistory()
```

> Notes: Explain requirements, preparses, postpares. There is also onFailure and completiontask. All of these are functions
or methods that can run as part of a command. These functions can do things like stop the command from running if some 
requirement isn't met or even change the type of command based on additional data gained at the time of execution.


Step 8) Controlling order of Execution: 
(This assumes you have the functions 'testRequirement', 'testPreparser', 'testPostpaser' from step 7.)

```python
cmdObj1 = tki.execute('sleep 10; echo "One"'); cmdObj2 = tki.execute('sleep 10; echo "Two"'); cmdObj3 = tki.execute('sleep 10; echo "Three"')
tki.waitForIdle(timeout=30)
print(cmdObj1.results)
tki.waitForIdle?
queOfCmds = ['sleep 2; echo "One"', 'sleep 2; echo "Two"', 'sleep 2; echo "Three"']
batchOfCmds = {'sleep 2; echo "One"', 'sleep 2; echo "Two"', 'sleep 2; echo "Three"'}
%time cmdObjQue = tki.execute(queOfCmds); print(cmdObjQue.waitForResults(wait=30))
%time cmdObjBatch = tki.execute(batchOfCmds); print(cmdObjBatch.waitForResults(wait=30))

for child in cmdObjQue.children:
    print(child.results)

for child in cmdObjBatch.children:
    print(child.results)
    
jsonStyleCommands = {'que1': ('sleep 2; echo "One"', 'sleep 2; echo "Two"', 'sleep 2; echo "Three"'), 'que2': ('id', 'who', 'last'), 'que3': ('df', 'du /tmp', 'cat /etc/os-release')}
import json
print(json.dumps(jsonStyleCommands, indent=4, sort_keys=True))
%time jsonStyleCmdObj = tki.execute(jsonStyleCommands); print(jsonStyleCmdObj.waitForResults(wait=30))
jsonStyleCmdObj.results.keys()

for key, item in jsonStyleCmdObj.results['que2'].items():
    print(f"Command: {key}")
    print(f"Output: {item}")


from PyCustomCollections.PyCustomCollections.CustomDataStructures import FrozenDict

jsonStyleCommands2 = {('id', 'who'),('df', 'cat /etc/os-release'), FrozenDict({'sleep1': 'sleep 2; echo "One"', 'sleep2': 'sleep 2; echo "Two"', 'sleep3': 'sleep 2; echo "Three"'}), FrozenDict({'command': '%s  /etc/os-release; echo $?', 'commandKey': 'touchCmd', 'requirements': FrozenDict({'testReq': testRequirement}), 'preparser': testPreparser, 'postparser': testPostpaser})}
%time jsonStyleCmdObj2 = tki.execute(jsonStyleCommands2); print(jsonStyleCmdObj2.waitForResults(wait=30))
jsonStyleCmdObj2.results['touchCmd']
```
    
> Notes: You can run group of commands in any order. The rule of thumb is if the data type is ordered (list, tuple, 
OrderedDict) then it runs like a Queue executing each Command one at a time. If the datatype is unordered (Dictionary, 
Set) then it runs as a Batch. You can create data structure that are similar in nature to Json that will run lots of 
commands in any order specified. There is a FrozenDict type from CustomDataStructures in the PyCustomCollections package
that allows for a static hashable Dictionary. This is useful if you want to also inject requirements,pre/post parsers 
and other kwargs into a specific command. 
