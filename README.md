# EC2 Instance launch utility

## Quick start

### Installation

Make sure to uninstall the previous version before upgrading

```
pip3 uninstall -y launch_control
PACKAGE={github/link}
VERSION={branch}
pip3 install git+https://${GITHUB_PAT}@github.com/${PACKAGE}.git@${VERSION} --user

lc --help
lc -v
```

### Configure

You will be required to setup your machine once-off so that launch control knows how to facilitate resource creation on your bahalf;

```
lc --configure
```

Please follow the prompts...

## Basic function

To launch an EC2 of type r4.8xlarge

### Spot instance
```
lc --launch --instance_type r4.8xlarge .
```
By default it will launch a spot instance

The last parameter passed here is the project to launch on EC2

### On-demand instance:
```
lc --launch --on_demand .
```


## Projects

**Syntax** is `lc --launch` `{project_path}` `{commands}`

One of the best parts of launch control is not simply launching EC2 resources, but actually launching your projects.
This functionality is in active development but broadly speaking we will support 3 types of projects;

1. Git project
2. docker-compose project
3. Makefile project

launching a project that has one of these file in the root directory of the project will attempt to clone and run the application layer for you.

```
lc --launch --instance_type "m5.xlarge" .
```

The last parameter points to the project you whish to launch on ec2

For the above example you will get back an EC2 instance with the `des-launch-control` project cloned and it will prompt you for a Make entrypoint. It prompts for the Make entrypoint because it detects a Makefile in the root directory.

### Provide your project entrypoint

If you are in a git project you can also provide your own entrypoint. You do this by speciying a bash command in your launch;

```
lc --launch --instance_type "m5.xlarge" . make run
```

For your projects you will want a docker-compose or Makefile (with `run` command) that starts your service/job as required. Make sure that the correct ports are exposed by your ec2 instance according to your security groups (e.g. exposing 8888 for jupyter lab)

**Notes**  
We have decided to run the entrypoint for your project via a psuedo terminal. Practically there is no difference sending commands over ssh or allocating a terminal but in the latter case we support run scripts that either display output (e.g. htop) or desire user input (prompts). Practically what that means is that we support docker apps or make apps that are interactive.
## Running bash commands against your ec2 instances

You can run bash commands on your ec2 instance(s) using the following patterns;

```
lc --bash des-launch-control/ uname
```

This should return `Linux` from the remote machine.

If you have multiple instances running you will be prompted on which instance to run on, or alternatively to run the command on all instances.  
**NOTE** Running a command on all instances is currently sequencial. A command that takes time to run should be backgrounded if you want to skip to the next instance.

Example;
```
lc --launch des-launch-control/ --instance_type "m5.xlarge"
lc --launch des-launch-control/ --instance_type "m5.xlarge"

lc -l

lc --bash des-launch-control/ 'echo I am running some cool code now'
```

** NOTES **  
The default entrypoint for the CLI is to assume a psuedo terminal, this means that the bash utlity will echo your input and the servers output.

To illustrate using example consider the expected output of the following;
```
lc --bash des-launch-control/ 'htop'
```
## Terminating/shutting down your EC2 resources

You can list all known resources;
```
lc --list
```

or

```
lc -l
```

to terminate an instance you can use the `--terminate` option.

```
lc --terminate des-launch-control
```

**WARNING** when specifying a project you will shut down ALL instances linked to the project!

or alternatively you can terminate all know instances launched by your machine against ALL known projects;
```
lc --terminate_all
```

## FAQ

*I’m getting a no module named launch_control after I install*

- make sure pip install is using the same python as your default in `PATH`  
- alternatively use a python virtual env

### Testing Dockerfile

The dockerfile is used for testing the package given the minimum requirements.
`Make test` will attempt to pip install the package and run a version check using the CLI

REQUIRES;
- environment variable `GITHUB_PAT`


