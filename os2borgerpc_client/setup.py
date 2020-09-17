from setuptools import setup

setup(
    name='os2borgerpc_client',
    # Keep this in sync with os2borgerpc_client/jobmanager.py
    version='0.0.5.1',
    description='Clients for the OS2borgerPC system',
    url='https://github.com/magenta-aps/',
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
    zip_safe=False
)
