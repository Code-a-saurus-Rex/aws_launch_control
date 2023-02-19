#This module relates to classes and helper functions for creating and managing project folders.
import os
import time
import subprocess
import textwrap

from launch_control.utils import run_bash
from launch_control.config import _BasicConfig

def determine_project_type(path: str):
    files = os.listdir(path)
    options = ['Makefile','docker-compose','Dockerfile','.git']

    types = []
    for opt in options:
        if any([True for f in files if opt in f]):
            types.append(opt)

    return types

def detect_create_project(path: str):
    '''look at a project path and create the correct project class'''
    types = determine_project_type(path)

    ## Check for runnable script inside project in order; make, compose, docker, none
    if any([True for t in types if 'Makefile' in t]):
        return MakeProject(path=path)
    # elif any([True for t in types if 'docker-compose' in t]):
    #     raise NotImplementedError
    # elif any([True for t in types if 'Dockerfile' in t]):
    #     raise NotImplementedError
    elif any([True for t in types if '.git' in t]):
        return GitProject(path=path)
    else:
        raise BaseException('Cannot determine project type')

class Project(_BasicConfig):
    '''project is the repo you want to deploy to ec2'''

    def __init__(self, **kwargs):

        if 'path' not in kwargs:
            raise BaseException('`path` not specified')
            
        else:
            super().__init__(**kwargs)

            self.name = os.path.basename(os.path.abspath(kwargs["path"]))

    def list_project_files(self):
        return os.listdir(self.path)

    def file_exists(self, match):
        files = self.list_project_files()
        matches = [True for f in files if match in f]

        return any(matches)

    def to_yaml(self):
        super().to_yaml(path=self.path)

    def from_yaml(self):

        super().from_yaml(path=self.path)

class GitProject(Project):

    def __init__(self, **kwargs):

        super().__init__(**kwargs)

    def _get_repo_name(self):
        bashCommand = "echo $(basename `git rev-parse --show-toplevel`)"
        try:
            process = subprocess.Popen(bashCommand, stdout=subprocess.PIPE,cwd=self.path,shell=True)
            output, error = process.communicate()
            return output.decode('utf-8').strip()
        except:
            raise BaseException(error)
        

    def _get_current_branch(self):
        bashCommand = "echo $(git rev-parse --symbolic-full-name --abbrev-ref HEAD)"
        try:
            process = subprocess.Popen(bashCommand, stdout=subprocess.PIPE,cwd=self.path,shell=True)
            output, error = process.communicate()
            return output.decode('utf-8').strip()
        except:
            raise BaseException(error)

        return run_bash(f"$(cd {self.path} & git rev-parse --symbolic-full-name --abbrev-ref HEAD)")

    def clone_remote(self, ec2_instance, ssh_key_file: str, pat: str):
        '''
        use github pat to clone the project on remote
        '''
        PACKAGE=self._get_repo_name()
        VERSION=self._get_current_branch()

        ec2_instance.poll_instance_ready(ssh_key_file=ssh_key_file)

        # ec2_instance.create_ssh_connection(ssh_key_file=ssh_key_file)
        # #check if instance is available
        # print('waiting for ssh')
        # response = ''
        # retries = 0
        # while not response:
        #     try:
        #         response = ec2_instance.run_bash_command('uname',pty=True)
        #     except:
        #         time.sleep(5)
        #     finally:
        #         retries += 1
        #         if retries > 13:
        #             print(f'tried {retries} times and could not connect to ec2 instance')
        #             break

        command = textwrap.dedent(f'''
            cd /home/ubuntu;
            ssh-keyscan -H github.com >> ~/.ssh/known_hosts;
            git clone https://{pat}@github.com/jumo/{PACKAGE}.git;
            cd {PACKAGE};
            git checkout {VERSION};
            ''')

        ec2_instance.run_bash_command(command,pty=True)

class MakeProject(GitProject):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # use EC2Instance to ssh into instance and call `make run`
    def run(self, *args, ec2_instance=None, ssh_key_file=None):
        ec2_instance.create_ssh_connection(ssh_key_file=ssh_key_file)

        command = textwrap.dedent(f'''
            cd /home/ubuntu/{self.name};
            {' '.join(args)};
            ''')

        ec2_instance.run_bash_command(command,pty=True)

