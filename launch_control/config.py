#Module repsonsible for managing the config and context of the local lc setup
import yaml

from launch_control.utils import write_yaml
from launch_control.vars import LAUNCH_CONTROL_CONFIG

def load_lc_config(config_path: str = LAUNCH_CONTROL_CONFIG()):
    lc_config = LaunchControlConfig()
    lc_config.from_yaml(config_path)

    return lc_config
class _BasicConfig:
    def __init__(self, **kwargs):
        self.path = LAUNCH_CONTROL_CONFIG()
        self.__dict__.update(**kwargs)

    def update(self,**kwargs):
        self.__dict__.update(**kwargs)

    def to_yaml(self,path=None):
        contents = self.__dict__
        write_yaml(contents,path)

    def from_yaml(self,path=None):
        with open(path) as f:
            config = yaml.load(f)
        self.update(**config)

class LaunchControlConfig(_BasicConfig):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


