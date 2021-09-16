SSH Connector
============

This is a 'Connector' for the **OS Diagnostic Tool Kit** or **OSDTK**. (Currently called Linux Diagnostic Tool Kit/LDTK). 
As the name suggest, this connector uses the SSH protocol to connect to its target. It uses the Python library 
Paramiko. 

This adds support for threading, supports the CommandContainer object which is used by the OSDTK to handle executing
commands and helps manage the environment on the remote target. IE: console variables, prompt, user permissions, etc...

The SSH Connector uses inheritance to break up the code into logical packages. Here is the list of classes in order from
top child class to the first parent.

1) [sshThreader](../reference/sshThreader/ "sshThreader") This is the top level class and as the name implies it handles
    threading. 

2) [sshEnvironmentManager](../reference/sshEnvironmentManager/ "sshEnvironmentManager") The next class has the logic for
    handling the multiple TTYs/Paramiko Channels. Each channel has its own environment that the SSH Connector can 
    execute code on simultaneously. 

3) [sshEnvironmentControl](../reference/sshEnvironmentControl/ "sshEnvironmentControl") This holds the code for changing
    the state of the remote Environment. It can change the user that the environment is loged in as or perhaps change 
    the console type such as from BASH to MySQL and so on. 

4) [sshBufferControl](../reference/sshBufferControl/ "sshBufferControl") This holds the logic for executing commands
    over the Paramiko SSH Channel.

5) [sshConnect](../reference/sshConnect/ "sshConnect") This holds the logic for logging into and disconnecting from a
    target machine. 

The SSH Connector also has libraries of its own.

1) [sshChannelEnvironment](../reference/sshChannelEnvironment/ "sshChannelEnvironment") This is a special set of classes
    that wrap around a Paramiko Channel. These classes store relevant information about the remote target shell 
    environment. This data is both used and manipulated by the main SSH Connector classes noted above. The main class is
    EnvironmentControls and inherits sshEnvironment which inherits sshChannelWrapper which inherits 
    Paramko.Channel. Thus this object is used inplace of the Paramko Channel object.

2) [SFTPChannel](../reference/SFTPChannel/ "SFTPChannel") This is a special package which includes a class and functions
    for interacting with a remote box via sFTP protocol.

3) [SCPChannel](../reference/SCPChannel/ "SCPChannel") This is a special package which includes a class and functions
    for interacting with a remote box as if using the 'scp' command.
