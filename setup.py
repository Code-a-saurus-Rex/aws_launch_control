import setuptools
setuptools.setup(
    name='launch_control',
    version='0.0.1',
    scripts=['lc'],
    author='Stefan Fouche',
    description='CLI for launching projects on EC2',
    packages=['launch_control'],
    install_requires=[
        'setuptools',
        'click',
        'pyyaml',
        'boto3',
        'fabric',
        'PyNaCl'
    ],
    python_requires='>=3.5'
)