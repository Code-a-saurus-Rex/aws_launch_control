#This module relates to classes and functions that interact with ec2
import os
from os import listdir
from os.path import isfile, isdir, join
import textwrap
import time
from pathlib import Path
import shutil
import boto3
import yaml
import fabric

from launch_control.vars import LAUNCH_CONTROL_INSTANCE_DIR
from launch_control.utils import read_yaml, write_yaml
from launch_control.project import Project

class EC2Instance:
    '''This class defines an object that represents a running/created ec2 instance'''
    def __init__(self,instance_id: str, region: str):
        self.instance_id = instance_id
        self.region = region

    def get_instance(self):
        _ec2 = boto3.resource('ec2', region_name=self.region)
        _instance = _ec2.Instance(self.instance_id)

        return _instance

    def create_ssh_connection(self, ssh_key_file: str):
        '''
        ssh_key_file: str = name of the file to use in ~/.ssh
        '''
        # ip = self._get_public_ip_address()
        ip = self._get_private_ip_address()
        ssh_con = fabric.Connection(ip, user="ubuntu", connect_kwargs={'key_filename': [ssh_key_file]})
        self.ssh_con = ssh_con

    def poll_instance_ready(self, ssh_key_file: str, max_retries = 13):
        '''tests ssh connection untill machine responds'''

        self.create_ssh_connection(ssh_key_file=ssh_key_file)
        #check if instance is available
        response = ''
        retries = 0
        while not response:
            try:
                response = self.run_bash_command('uname',pty=True)
            except:
                if retries == 0: 
                    print('No response yet, double check your VPN is connected')
                time.sleep(5)
            finally:
                retries += 1
                if retries > max_retries:
                    self.terminate()
                    raise BaseException(f'tried {retries} times and could not connect to ec2 instance, terminating...')
                    break

    # def __getstate__(self):
    #     state = self.__dict__.copy()
    #     del state['hidden']
    #     return state

    def to_yaml(self,path=None):
        contents = self.__dict__
        drop_keys = [key for key in contents if key.startswith('_')]
        for key in drop_keys:
            contents.pop(key)
        write_yaml(contents,path)

    def from_yaml(self,path=None):
        with open(path) as f:
            config = yaml.load(f)
        self.update(**config)

    def _get_private_ip_address(self):
        _instance = self.get_instance()
        return _instance.private_ip_address
        
    def _get_public_ip_address(self):
        _instance = self.get_instance()
        return _instance.public_ip_address

    def _copy_file(self,local_path: str,remote_path: str):
        '''copies file from local path to remote path for the current ec2 instance id'''
        raise NotImplementedError

    def _copy_files(self, copy_specification: dict):
        '''copy files into the ec2 instance from {key} to {value} on the remote'''

        for key, value in copy_specification.items():
            self._copy_file(key,value)

    def _setup_git(self, username: str, usermail: str):
        '''take your local git configuration and replicate it on the ec2 machine'''
        if not self.ssh_con:
            raise BaseException('ssh connection not established yet')

        
        # setup name and email
        result = self.run_bash_command(f'git config --global user.name {username}')
        result = self.run_bash_command(f'git config --global user.email {usermail}')

        # # setup ssh key on ec2 machine (not any docker image we may run later)
        # scp_conn = fabric.transfer.Transfer(self.ssh_con)
        # scp_conn.put(ssh_key_path, remote='/root/.ssh/id_rsa')

    def _set_environment_variable(self, name: str, value: str):
        # export GITHUB_PAT=$GITHUB_PAT
        response = self.run_bash_command(f'echo "export {name}={value}" >> ~/.profile')

    def _set_environment_variables(self, environment_variables: dict):
        '''set environment variables inside the ec2 instance'''
        
        for key, value in environment_variables.items():
            self._set_environment_variable(key,value)

    def get_instance_state(self):
        _instance = self.get_instance()
        try:
            print(_instance)
            state = _instance.state['Name']
        except:
            raise BaseException('Could not get instance state')

        return state

    def run_bash_command(self, command:str, pty=False):
        '''
        pty: bool = should we use a terminal echoing standard in or run the command wihtout a psuedo terminal?
        '''
        command_template = textwrap.dedent(f'''
        source ~/.profile;
        {command}
        ''')

        if not self.ssh_con:
            raise BaseException('ssh connection not established yet')
        
        ssh_con = self.ssh_con

        result = ssh_con.run(command_template,pty=pty)

        return result

    def terminate(self):
        '''terminate the ec2/spot instance'''

        if not self.get_instance_state() == 'running':
            print('instance is not running')
        else:
            _instance = self.get_instance()
            _instance.terminate()



class EC2InstanceFactory:
    '''This class is responsible for spinning up on demand and spot instances and creating `EC2Instance` objects'''
    def __init__(self, region: str, profile_name:str, key_pair_name: str):
        self.region = region
        self.profile_name = profile_name
        self.key_pair = key_pair_name

        self._session=boto3.session.Session(profile_name=profile_name,region_name=region)
        self._ec2=self._session.resource('ec2')
        self._ec2_client = boto3.client('ec2',region_name = region)
        self.instances = []

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['hidden']
        return state

    def poll_instance_until_running(self, instance_id, delay = 5, max_attempts = 30):
        waiter = self._ec2_client.get_waiter('instance_running')
        waiter.wait(
            InstanceIds=[
                instance_id,
            ],
            WaiterConfig={
                'Delay': delay,
                'MaxAttempts': max_attempts
            }
        )
        print('instance running')

    def poll_instance_untill_stopped(self, instance_id, delay = 5, max_attempts = 30):
        waiter = self._ec2_client.get_waiter('instance_stopped')
        waiter.wait(
            InstanceIds=[
                instance_id,
            ],
            WaiterConfig={
                'Delay': delay,
                'MaxAttempts': max_attempts
            }
        )
        print('instance terminate')

    #Launch with or without a project, default behavior -> project.run()
    def boto_request_instance(self, tags: dict, key_pair_name: str, aws_profile: str, aws_region: str, image_id: str, instance_type: str, security_group_id: str, iam_role_arn: str):

        new_instance = self._ec2.create_instances(
                ImageId = image_id,
                MinCount = 1,
                MaxCount = 1,
                InstanceType = instance_type,
                KeyName = key_pair_name,
                SecurityGroupIds=[security_group_id],
                IamInstanceProfile={
                    'Arn': iam_role_arn
                },
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags':
                            tags,
                    },
                ],
        )
        # print(new_instance)
        # self.instances.append(new_instance["Instances"][0]["InstanceId"])
        self.instances.append(new_instance[0].instance_id)

        return EC2Instance(instance_id = new_instance[0].instance_id, region=self.region)

    def boto_request_spot_instance(self, tags: dict, key_pair_name: str, aws_profile: str, aws_region: str, image_id: str, instance_type: str, spot_price: str, security_group_id: str, iam_role_arn: str):
        
        response = self._ec2_client.request_spot_instances(
                InstanceCount = 1,
                LaunchSpecification={
                        'SecurityGroupIds': [
                            security_group_id,
                        ],
                        'IamInstanceProfile': {
                            'Arn': iam_role_arn,
                        },
                        'ImageId': image_id,
                        'InstanceType': instance_type,
                        'KeyName': key_pair_name,
                },
                SpotPrice=spot_price,
        )

        state = 'open'
        while state == 'open':
            time.sleep(5)
            spot = self._ec2_client.describe_spot_instance_requests(SpotInstanceRequestIds = [response['SpotInstanceRequests'][0]['SpotInstanceRequestId']])
            state = spot['SpotInstanceRequests'][0]['State']
            print('Spot request ' + str(response['SpotInstanceRequests'][0]['SpotInstanceRequestId']) )

        # Exit if there is an error
        if (state != 'active'):
            exit(1)

        # List of resources to tag
        ids_to_tag = [spot['SpotInstanceRequests'][0]['InstanceId']]

        self._ec2_client.create_tags(Resources = ids_to_tag, Tags = tags)

        self.instances.append(spot['SpotInstanceRequests'][0]['InstanceId'])

        return EC2Instance(instance_id = spot['SpotInstanceRequests'][0]['InstanceId'], region=self.region)

    @staticmethod
    def list_instances(verbose: bool = True, project: str=None, region: str=None):
        '''step through known instances and list them and their status'''

        path = LAUNCH_CONTROL_INSTANCE_DIR()
        
        projects_paths = [join(path, dir) for dir in listdir(path) if isdir(join(path, dir))]
        projects = [dir for dir in listdir(path) if isdir(join(path, dir))]

        resources = {}
        resource_paths = {}

        for proj, proj_path in zip(projects,projects_paths):
            if project is not None:
                if proj != project:
                    next
            resources[proj] = []
            resource_paths[proj_path] = []
            instances = [f.replace('.yaml','') for f in listdir(proj_path) if isfile(join(proj_path, f))]
            instance_paths = [join(proj_path, f) for f in listdir(proj_path) if isfile(join(proj_path, f))]
            for ins, instance_path in zip(instances, instance_paths):
                resources[proj].append(ins)
                resource_paths[proj_path].append(instance_path)

        if verbose:
            print('found resources;')
            print(resources)
            print()

            if len(resources) > 0:
                print('collecting information...')
                for proj, proj_path in zip(resources,resource_paths):
                    for ins in resources[proj]:
                        instance = EC2Instance(ins, region).get_instance()
                        print(instance)

        else:
            return resources, resource_paths

    def list_ips(self):
        resources, resource_paths = self.list_instances(verbose=False)
        for proj, proj_path in zip(resources,resource_paths):
            for ins in resources[proj]:

                instance = EC2Instance(ins, self.region)

                print({'instance_id': instance.instance_id ,'private_ip_address' : instance.instance.private_ip_address, 'public_ip_address' : instance.instance.public_ip_address})

    def shutdown_instance(self, instance_id: str):
        instance = EC2Instance(instance_id, self.region)
        print(f'loaded instance id {instance_id}')
        print('terminating...')
        instance.terminate()

    def shutdown_project(self, project_name: str = None):
        '''shutdown all aws resources for this project'''

        resources, resource_paths = self.list_instances(verbose=False)
        for proj, proj_path in zip(resources,resource_paths):
            #if we match the project
            if proj == project_name:
                for ins, ins_path in zip(resources[proj],resource_paths[proj_path]):
                    try:
                        self.shutdown_instance(ins)
                    except:
                        print(f'cannot load and terminate instance {ins} for project {proj}')
                        print('deleting instance reference...')
                    finally:
                        os.remove(ins_path) 

                shutil.rmtree(proj_path) 
            
        print('Done!')

    def shutdown_all(self):
        resources, resource_paths = self.list_instances(verbose=False)
        for proj, _ in zip(resources,resource_paths):
            self.shutdown_project(proj)
