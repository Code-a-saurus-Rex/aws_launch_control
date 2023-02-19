import sys
import subprocess
import pkg_resources 
from pathlib import Path
import ntpath

import click
import yaml
import os

import warnings
warnings.filterwarnings("ignore") 

from launch_control.config import LaunchControlConfig, load_lc_config
from launch_control.utils import update_yaml_file, get_git_config, detect_ssh_keys, read_yaml, test_credentials
from launch_control.vars import LAUNCH_CONTROL_CONFIG, LAUNCH_CONTROL_PROJECT_DIR, LAUNCH_CONTROL_INSTANCE_DIR
from launch_control.ec2 import EC2InstanceFactory, EC2Instance
from launch_control.project import MakeProject, detect_create_project, determine_project_type, GitProject

__author__ = "Stefan Fouche"

def configure_launch_control(file=None, update_file=None):
    ##Check if launch control environment configs exist
    try:
        Path(LAUNCH_CONTROL_INSTANCE_DIR()).mkdir(parents=True)
    except:
        print('found existing configs directory')

    ## setup from a yaml file?
    if file:
        try:
            lc_config = load_lc_config(file)
            print(f'initialized config from {file}')
            lc_config.to_yaml(LAUNCH_CONTROL_CONFIG())
            sys.exit(f'credentials loaded from file! Stored at {LAUNCH_CONTROL_CONFIG()}')
        except:
            # create missing folder structure
            sys.exit('could not load credentials... is it a valid yaml file?')

    ## update your existing setup from a yaml file?
    if update_file:
        try:
            contents = read_yaml(update_file)

            update_yaml_file(LAUNCH_CONTROL_CONFIG(), contents)
            sys.exit(f'updated credentials from {update_file}')
        except:
            sys.exit('could not load credentials... is it a valid yaml file?')

    ## otherwise setup creds via prompts
    minimum_required_creds = {
        'USER_NAME': 'full name to identify you with',
        'EC2_KEY_PAIR_NAME': 'name of key used for your ec2 instance',
        'EC2_KEY_PAIR': 'file name in your ~/.ssh folder',
        'GITHUB_PAT' : 'your personal access token for jumo github acc',
        'GIT_USERNAME' : 'your git username',
        'GIT_USEREMAIL' : 'your git email',
        'AWS_DEFAULT_REGION' : 'your aws region',
        'AWS_PROFILE' : 'your aws profile',
        'IMAGE_ID': 'default image id to use for ec2 instances',
        'SECURITY_GROUP_ID': 'default security group id to use for ec2 instances',
        'IAM_ROLE_ARN': 'default iam role arn to use for ec2 instances',
    }

    print('you will be asked to provide the following:')
    print('--------------------')
    print(minimum_required_creds)
    print('--------------------')

    git_config = get_git_config()

    keys = detect_ssh_keys()
    print('We have detected the following ssh key paths inside ~/.ssh/:')
    print(keys)

    default_ssh = "~/.ssh/des-ec2.pem"
    if not any([default_ssh in x for x in keys]):
        default_ssh = [x for x in keys if '.pem' in x][0]

    setup_config = {}
    setup_config['FULL_NAME'] = click.prompt('Please enter FULL_NAME e.g. John Smith', type=str)
    setup_config['TEAM'] = click.prompt('Please enter your TEAM', default='decision-science')
    setup_config['EC2_KEY_PAIR_NAME'] = click.prompt('Please enter EC2_KEY_PAIR_NAME', type=str, default="decision-science")
    setup_config['EC2_KEY_PAIR_PATH'] = click.prompt('Please enter EC2_KEY_PAIR_PATH', type=str, default = default_ssh)
    setup_config['GITHUB_PAT'] = click.prompt('Please enter GITHUB_PAT', type=str, default=os.environ["GITHUB_PAT"])
    setup_config['GIT_USERNAME'] = click.prompt('Please enter GIT_USERNAME', type=str, default=git_config["GIT_USERNAME"])
    setup_config['GIT_USEREMAIL'] = click.prompt('Please enter GIT_USEREMAIL', type=str, default=git_config["GIT_USEREMAIL"])
    setup_config['AWS_DEFAULT_REGION'] = click.prompt('Please enter AWS_DEFAULT_REGION', default='eu-west-1')
    setup_config['AWS_PROFILE'] = click.prompt('Please enter AWS_PROFILE', default='default')
    setup_config['IMAGE_ID'] = click.prompt('Please enter your default image id for ec2 instances', default='ami-04ecd748e84589bf8')
    setup_config['SECURITY_GROUP_ID'] = click.prompt('Please enter your default security group id for ec2 instances', default='sg-b01502d7')
    setup_config['IAM_ROLE_ARN'] = click.prompt('Please enter your default iam role for ec2 instances', default='arn:aws:iam::309952364818:instance-profile/jumo-decisionscience-spot-role')

    lc_config = LaunchControlConfig(**setup_config)
    lc_config.to_yaml(LAUNCH_CONTROL_CONFIG())
    sys.exit(f'credentials stored at {LAUNCH_CONTROL_CONFIG()}')
    # if setup_config_path.is_file():

@click.command()
@click.option('-v','--version', is_flag=True)
@click.option('--configure', is_flag=True)
@click.option('-f','--file')
@click.option('-u','--update_file')
@click.option('--launch', is_flag=True)
@click.argument('project_path', default='')
@click.option('--instance_type', default='')
@click.argument('command', nargs=-1)
@click.option('--on_demand', is_flag=True, default=False)
@click.option('--spot_price', default='2')
@click.option('--terminate', is_flag=True)
@click.option('--terminate_all', is_flag=True)
@click.option('--region')
@click.option('--profile')
@click.option('--key_pair_name')
@click.option('-l','--list', is_flag=True)
@click.option('--bash', is_flag=True)
@click.option('--ssh', is_flag=True)
@click.option('-i', '--info', is_flag=True)

def cli(project_path='', info=None, ssh=None, command=None, list=False, terminate=None, version: bool = False, configure=False, file=None, update_file=None, launch=None, instance_type='', bash=None, terminate_all=None,region=None, key_pair_name=None, profile=None,  on_demand=False, spot_price='2'):

    if version:
        ver = pkg_resources.require('launch_control')[0].version  
        sys.exit(ver)

    if configure:
        configure_launch_control(file,update_file)
        sys.exit('configured')

    try:
        lc_config = load_lc_config(LAUNCH_CONTROL_CONFIG())

    except:
        sys.exit('could not load credentials... Have you run `lc --configure`?')

    if project_path != '':
        if project_path == '.':
            project_path = os.getcwd()

        project_name = os.path.basename(os.path.abspath(project_path))
        project_type = determine_project_type(project_path)
        project = detect_create_project(project_path)
        # print('We have detected the following project types:')
        # print(project_type)
    else:
        # print('no project specified...')
        project_name = 'no_project'

    if not region:
        region = lc_config.AWS_DEFAULT_REGION

    if not profile:
        profile = lc_config.AWS_PROFILE

    if not key_pair_name:
        key_pair_name = lc_config.EC2_KEY_PAIR_NAME

    if launch:
        test_credentials()

        if instance_type == '':
            available_instances = ["m5.xlarge","r4.4xlarge","r4.8xlarge","r3.8xlarge","r5d.16xlarge","r5d.24xlarge"]

            # click.prompt('please choose instance size', default='m5.xlarge')
            instance_type = click.prompt(
                'Please choose instance size (small to large):',
                type=click.Choice([instance for instance in available_instances]),
                show_default=True,
            )

        # print('tagging instance using:')

        if not project_path:
            instance_name = f'{lc_config.FULL_NAME} - Launch Control'
        else:
            instance_name = f'{lc_config.FULL_NAME} - {project_name}'

        tags = [
            {'Key':'Name', 'Value': instance_name},
            {'Key':'Username', 'Value': lc_config.FULL_NAME},
            {'Key':'Team', 'Value': lc_config.TEAM},
            {'Key':'Owner', 'Value': lc_config.TEAM},
            {'Key':'Environment', 'Value': 'production'},
            {'Key':'Classification', 'Value': 'restricted'},
            {'Key':'Status', 'Value': 'active'},
        ]

        # print(tags)

        ec2_factory = EC2InstanceFactory(region=region,profile_name=profile,key_pair_name=key_pair_name)

        if not on_demand:
            ec2_instance = ec2_factory.boto_request_spot_instance(
                tags=tags,
                key_pair_name=lc_config.EC2_KEY_PAIR_NAME,
                aws_profile=lc_config.AWS_PROFILE,
                aws_region=lc_config.AWS_DEFAULT_REGION,
                image_id=lc_config.IMAGE_ID,
                instance_type=instance_type,
                spot_price=spot_price,
                security_group_id=lc_config.SECURITY_GROUP_ID,
                iam_role_arn=lc_config.IAM_ROLE_ARN
            )

        else:
            ec2_instance = ec2_factory.boto_request_instance(
                tags = tags,
                key_pair_name=lc_config.EC2_KEY_PAIR_NAME,
                aws_profile=lc_config.AWS_PROFILE,
                aws_region=lc_config.AWS_DEFAULT_REGION,
                image_id=lc_config.IMAGE_ID,
                instance_type=instance_type,
                security_group_id=lc_config.SECURITY_GROUP_ID,
                iam_role_arn=lc_config.IAM_ROLE_ARN
            )

        print('request submitted...')
        ec2_instance.to_yaml(f'{LAUNCH_CONTROL_PROJECT_DIR(project_name=project_name)}/{ec2_instance.instance_id}.yaml')

        print(f'polling instance {ec2_instance.instance_id} untill running...')
        ec2_factory.poll_instance_until_running(instance_id=ec2_instance.instance_id)

        Path(LAUNCH_CONTROL_PROJECT_DIR(project_name=project_name)).mkdir(parents=True,exist_ok=True)

        ## check if ec2 machine is ready
        ec2_instance.poll_instance_ready(ssh_key_file=lc_config.EC2_KEY_PAIR_PATH)

        ## setup environment variables
        env_vars = {
            'GITHUB_PAT':lc_config.GITHUB_PAT,
            'BUNDLE_GITHUB__COM':lc_config.GITHUB_PAT,
            'GIT_USERNAME':lc_config.GIT_USERNAME,
            'AWS_DEFAULT_REGION':lc_config.AWS_DEFAULT_REGION,
        }

        ec2_instance._set_environment_variables(env_vars)
        ec2_instance._setup_git(username=lc_config.GIT_USERNAME,usermail=lc_config.GIT_USEREMAIL)

        # if git project clone on remote ec2 machine
        if project_name != 'no_project':
            if isinstance(project, GitProject):
                project.clone_remote(ec2_instance, ssh_key_file=lc_config.EC2_KEY_PAIR_PATH,pat=lc_config.GITHUB_PAT)

            ## if command is provided run that, else detect run policy
            if command:
                run_command = ' '.join(command)
                if isinstance(project, GitProject):
                    run_command = f'cd /home/ubuntu/{project.name} && ' + run_command
                
                ec2_instance.create_ssh_connection(ssh_key_file=lc_config.EC2_KEY_PAIR_PATH)
                ec2_instance.run_bash_command(run_command,pty=True)

            else:

                if isinstance(project, MakeProject):
                    ## prompt for make command to run
                    print('We have detected a Makefile in your project...')
                    run_make = click.confirm('Do you want to launch with Make?')
                    if run_make:
                        make_command = click.prompt('Specify Make command', type=str, default='make run')
                        project.run(ec2_instance=ec2_instance, ssh_key_file=lc_config.EC2_KEY_PAIR_PATH, *make_command.split())

        ## Always print private IP of instance when done
        private_ip = ec2_instance._get_private_ip_address()
        public_ip = ec2_instance._get_public_ip_address()
        print('All tasks finished, Private IP adress is:')
        print(private_ip)
        print('Public IP is:')
        print(public_ip)
        clean_ip = public_ip.replace('.','-')
        clean_ip = f'ec2-{clean_ip}.{region}.compute.amazonaws.com'
        print('url is:')
        print(clean_ip)

    if terminate:
        ec2_factory = EC2InstanceFactory(region=region,profile_name=profile,key_pair_name=key_pair_name)
        ec2_factory.shutdown_project(project_name=project_name)

    if terminate_all:
        ec2_factory = EC2InstanceFactory(region=region,profile_name=profile,key_pair_name=key_pair_name)
        ec2_factory.shutdown_all()


    if list:
        ec2_factory = EC2InstanceFactory(region=region,profile_name=profile,key_pair_name=key_pair_name)
        ec2_factory.list_instances()

    if ssh:
        ec2_factory = EC2InstanceFactory(region=region,profile_name=profile,key_pair_name=key_pair_name)
        proj_inst, proj_paths = ec2_factory.list_instances(project = project_name,verbose=False)

        instances = proj_inst.get(project_name)

        if instances is None:
            sys.exit('no instances found for this project')

        if len(instances) > 1:
            print()
            choices = []
            for ins in instances:
                choices.append(ins)

            instances = click.prompt(
                'please select instance to run on:',
                type=click.Choice([instance for instance in choices]),
            )

        instance = EC2Instance(instances[0], region)
        ip = instance._get_public_ip_address()
        clean_ip = ip.replace('.','-')
        clean_ip = f'ec2-{clean_ip}.{region}.compute.amazonaws.com'

        key_file = ntpath.basename(lc_config.EC2_KEY_PAIR_PATH)
        run_command = f'ssh -t -i ~/.ssh/{key_file} ubuntu@{clean_ip}'
        # instance.create_ssh_connection(ssh_key_file=lc_config.EC2_KEY_PAIR_PATH)
        # instance.run_bash_command(run_command,pty=True)

        ##exit
        # sys.exit(run_command)
        print(run_command)

    if info:
        ec2_factory = EC2InstanceFactory(region=region,profile_name=profile,key_pair_name=key_pair_name)
        proj_inst, proj_paths = ec2_factory.list_instances(project = project_name,verbose=False)

        instances = proj_inst.get(project_name)

        if instances is None:
            sys.exit('no instances found for this project')

        if len(instances) > 1:
            print()
            choices = []
            for ins in instances:
                choices.append(ins)

            instances = click.prompt(
                'please select instance to run on:',
                type=click.Choice([instance for instance in choices]),
            )

        instance = EC2Instance(instances[0], region)
        ip = instance._get_public_ip_address()
        clean_ip = ip.replace('.','-')
        clean_ip = f'ec2-{clean_ip}.{region}.compute.amazonaws.com'

        print(clean_ip)

    if bash:

        if command is None:
            sys.exit('you must provide a bash command')

        run_command = ' '.join(command)
        if isinstance(project, GitProject):
            run_command = f'cd /home/ubuntu/{project.name} && ' + run_command

        ec2_factory = EC2InstanceFactory(region=region,profile_name=profile,key_pair_name=key_pair_name)
        proj_inst, proj_paths = ec2_factory.list_instances(project = project_name,verbose=False)

        instances = proj_inst.get(project_name)

        if instances is None:
            sys.exit('no instances found for this project')

        if len(instances) > 1:
            print()
            choices = ['all']
            for ins in instances:
                choices.append(ins)
            instance_choice = click.prompt(
                'please select instance to run on:',
                type=click.Choice([instance for instance in choices]),
            )

            if instance_choice != 'all':
                instances = [instance_choice]

        for ins in instances:
            instance = EC2Instance(ins, region)
            instance.create_ssh_connection(ssh_key_file=lc_config.EC2_KEY_PAIR_PATH)
            instance.run_bash_command(run_command,pty=True)


if __name__ == '__main__':
    cli()
