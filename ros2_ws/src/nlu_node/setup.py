from setuptools import find_packages, setup

package_name = 'nlu_node'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['requests', 'setuptools'],
    zip_safe=True,
    maintainer='skochhar',
    maintainer_email='skochhar@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'mock_hsm = nlu_node.mock_hsm_node:main',
            'mock_hsm_action = nlu_node.mock_hsm_action_server:main',
            'nlu_node = nlu_node.nlu_ros_node:main',
        ],
    },
)
