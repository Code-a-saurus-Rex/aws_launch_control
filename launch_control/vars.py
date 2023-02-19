from pathlib import Path

def LAUNCH_CONTROL_CONFIG():

    home = str(Path.home())

    p = f'{home}/.launch_control/config.yaml'

    return p

def LAUNCH_CONTROL_DIR():

    home = str(Path.home())
    p = f'{home}/.launch_control'

    return p

def LAUNCH_CONTROL_INSTANCE_DIR():

    home = str(Path.home())
    p = LAUNCH_CONTROL_DIR() + '/instances'

    return p

def LAUNCH_CONTROL_PROJECT_DIR(project_name: str):

    p = LAUNCH_CONTROL_INSTANCE_DIR() + '/' + project_name

    return p