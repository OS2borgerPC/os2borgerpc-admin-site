from setuptools import setup

with open("README", "r") as fh:
    long_description = fh.read()

setup(
    name='os2borgerpc_client',
    # Keep this in sync with os2borgerpc_client/jobmanager.py
    version='1.0.1',
    description='Client for the OS2borgerPC system',
    long_description=long_description,
    url='https://github.com/OS2borgerPC/',
    author='Magenta ApS',
    author_email='info@magenta-aps.dk',
    license='GPLv3',
    packages=['os2borgerpc.client', 'os2borgerpc.client.security'],
    install_requires=['PyYAML'],
    scripts=[
        'bin/get_os2borgerpc_config',
        'bin/set_os2borgerpc_config',
        'bin/get_package_data',
        'bin/os2borgerpc_find_gateway',
        'bin/os2borgerpc_register_in_admin',
        'bin/os2borgerpc_push_config_keys',
        'bin/os2borgerpc_upload_dist_packages',
        'bin/os2borgerpc_upload_packages',
        'bin/jobmanager',
        'bin/register_new_os2borgerpc_client.sh',
        'bin/admin_connect.sh',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
    zip_safe=False,
    python_requires='>=3.6',
)
