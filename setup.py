#!/usr/bin/env python3
from setuptools import setup

setup(
    name='upb-lib',
    version='0.1.0',
    packages=['upb_lib'],
    install_requires=['pyserial-asyncio>=0.4.0'],
    package_data={
        '': ['CHANGELOG.md', 'bin/**/*'],
    },
    exclude_package_data={'': ['test']},
    author='Glenn Waters',
    author_email='gwwaters+upb@gmail.com',
    description='Library for interacting with UPB PIM.',
    url='https://github.com/gwww/upb-lib',
    license='MIT',
    python_requires='>=3.7',
)
