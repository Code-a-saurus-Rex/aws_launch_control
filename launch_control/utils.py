#common utilities
import yaml
import subprocess
import os
from os import listdir
from os.path import isfile, join
from pathlib import Path

from launch_control.vars import LAUNCH_CONTROL_CONFIG, LAUNCH_CONTROL_PROJECT_DIR, LAUNCH_CONTROL_INSTANCE_DIR

def read_yaml(path: str):
    with open(path) as f:
        contents = yaml.load(f)

    return contents

def write_yaml(contents, path):
    dir = os.path.dirname(os.path.abspath(path))
    Path(dir).mkdir(parents=True,exist_ok=True)
    with open(path,'w') as f:
        yaml.dump(contents,f)

def update_yaml_file(file: str, contents: dict):

    for key, value in contents.items():
        with open(file,'r') as yamlfile:
            cur_yaml = yaml.safe_load(yamlfile) 
            cur_yaml[key].update(value)

        if cur_yaml:
            with open(file,'w') as yamlfile:
                yaml.safe_dump(cur_yaml, yamlfile) 

def run_bash(bashCommand,cwd=None,shell=True):
    try:
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE,cwd=cwd,shell=shell)
        output, error = process.communicate()
        return output.decode('utf-8').strip()
    except error:
        raise error
    
def test_credentials():
    '''raises an error if credentials are expired'''
    try:
        response = subprocess.run(['aws','sts','get-caller-identity'], capture_output=True)
    except subprocess.CalledProcessError as e:
        print(e.output)
        
    finally:
        if response.returncode != 0:
            print(response.returncode)
            raise BaseException('\nCould not validate aws credentials... \nHave they expired? \nTry running gimme-aws-creds to refresh them.')

def get_git_config():
    """Get git username and email via command line"""

    return {
        "GIT_USERNAME": run_bash("git config --global user.name",shell=False),
        "GIT_USEREMAIL": run_bash("git config --global user.email",shell=False)
    }

def detect_ssh_keys(path: str = None):

    if path:
        ssh_keys = [join(path, f) for f in listdir(path) if isfile(join(path, f))]
    else:
        home = str(Path.home())
        path = f'{home}/.ssh/'
        ssh_keys = [join(path, f) for f in listdir(path) if isfile(join(path, f))]

    return ssh_keys
