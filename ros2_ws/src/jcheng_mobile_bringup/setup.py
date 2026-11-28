from glob import glob
import os

from setuptools import setup

package_name = 'jcheng_mobile_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*.yaml'))),
        (os.path.join('share', package_name, 'urdf'), glob(os.path.join('urdf', '*.xacro'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ubuntu',
    maintainer_email='maintainer@example.invalid',
    description='Contract-compliant mobile-base bringup (scan in, intent out)',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'intent_node = jcheng_mobile_bringup.intent_node:main',
        ],
    },
)
