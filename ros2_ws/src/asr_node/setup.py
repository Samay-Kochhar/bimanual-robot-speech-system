from setuptools import find_packages, setup

package_name = 'asr_node'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='skochhar',
    maintainer_email='skochhar@todo.todo',
    description='Manual and Faster-Whisper ROS 2 ASR transcript publishers',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'faster_whisper_asr = asr_node.faster_whisper_asr_node:main',
            'manual_asr = asr_node.manual_asr_node:main',
        ],
    },
)
