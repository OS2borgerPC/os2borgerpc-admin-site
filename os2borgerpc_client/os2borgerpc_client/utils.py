#!/usr/bin/env python
"""This file contains utilities for communicating with the OS2borgerPC admin
system."""

from __future__ import print_function

import os
import sys
import csv
import urlparse
import re
import subprocess
import fcntl

from os2borgerpc_client.config import OS2borgerPCConfig
from os2borgerpc_client.admin_client import OS2borgerPCAdmin


class filelock(object):
    """Utility class to implement locks with Unix system calls. This is to
    avoid the problem with stale locks not detected by the filelock module.
    """
    def __init__(self, file_name):
        self.file_name = file_name
        self.file_descriptor = None

    def acquire(self):
        assert not self.file_descriptor
        self.file_descriptor = file(self.file_name, 'w')
        fcntl.lockf(self.file_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def release(self):
        assert self.file_descriptor
        fcntl.lockf(self.file_descriptor, fcntl.LOCK_UN)
        self.file_descriptor = None

    def i_am_locking(self):
        return self.file_descriptor is not None


def get_upgrade_packages():
    matcher = re.compile('Inst\s+(\S+)')
    prg = subprocess.Popen(
        ['apt-get', '--just-print',  'dist-upgrade'],
        stdout=subprocess.PIPE
    )
    result = []
    for line in prg.stdout.readlines():
        m = matcher.match(line)
        if m:
            result.append(m.group(1))
    return result


def upload_packages():
    config = OS2borgerPCConfig()
    data = config.get_data()

    admin_url = data['admin_url']
    xml_rpc_url = data.get('xml_rpc_url', '/admin-xml/')
    uid = data['uid']

    admin = OS2borgerPCAdmin(urlparse.urljoin(admin_url, xml_rpc_url))

    # TODO: Make option to turn off/avoid repeating this.
    os.system('get_package_data /tmp/packages.csv')

    upgrade_pkgs = set(get_upgrade_packages())

    with open('/tmp/packages.csv') as f:
        package_reader = csv.reader(f, delimiter=';')
        package_data = [
            {
                'name': n,
                'status': 'needs upgrade' if n in upgrade_pkgs else s,
                'version': v,
                'description': d
            } for (n, s, v, d) in package_reader
        ]

    try:
        admin.send_status_info(uid, package_data, None)
    except Exception as e:
        print('Error:', str(e), file=sys.stderr)
        sys.exit(1)


def upload_dist_packages():
    config = OS2borgerPCConfig()
    data = config.get_data()

    admin_url = data['admin_url']
    xml_rpc_url = data.get('xml_rpc_url', '/admin-xml/')
    distribution = data['distribution']

    admin = OS2borgerPCAdmin(urlparse.urljoin(admin_url, xml_rpc_url))

    # TODO: Make option to turn off/avoid repeating this.
    os.system('get_package_data /tmp/packages.csv')

    with open('/tmp/packages.csv') as f:
        package_reader = csv.reader(f, delimiter=';')
        package_data = [
            {'name': n, 'status': s, 'version': v, 'description': d} for
            (n, s, v, d) in package_reader]

    try:
        admin.upload_dist_packages(distribution, package_data)
    except Exception as e:
        print('Error:', str(e), file=sys.stderr)
        sys.exit(1)
