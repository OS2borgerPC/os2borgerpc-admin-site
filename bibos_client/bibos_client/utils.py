#!/usr/bin/env python
"""This file contains utilities for communicating with the BibOS admin
system."""

import os
import sys
import csv
import urlparse
import re
import subprocess
import fcntl

import contextlib
import time
import signal
import errno

from bibos_utils.bibos_config import BibOSConfig
from bibos_client.admin_client import BibOSAdmin


@contextlib.contextmanager
def filelock(file_name, max_age=None):
    """Acquires the named lock for the lifetime of the context. If the named
    lock was acquired with this function by another process more than max_age
    seconds ago, then that process will be forcibly terminated."""
    pid_file = file_name + ".pid"
    with open(file_name, "w") as fd:
        try:
            # Try to take the lock in the usual way
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as lock_ex:
            # If this lock has a maximum age, then check if it's been exceeded.
            # If it has, then forcibly terminate the locking process and take
            # the lock
            if lock_ex.errno == errno.EAGAIN and max_age is not None:
                lock_age = time.time() - os.stat(pid_file).st_mtime
                if lock_age >= max_age:
                    try:
                        with open(pid_file, "rt") as fp:
                            pid = int(fp.read().strip())
                        os.kill(pid, signal.SIGKILL)
                        fcntl.lockf(fd, fcntl.LOCK_EX)
                    except ValueError:
                        raise lock_ex
                else:
                    raise lock_ex
            else:
                raise lock_ex

        # XXX RACE BEGINS: we have the lock but haven't written our PID to the
        # corresponding pidfile yet
        with open(pid_file, "wt") as fp:
            fp.write(str(os.getpid()))
        # XXX RACE ENDS: other processes started after this point will behave
        # as expected

        try:
            yield
        finally:
            os.unlink(pid_file)
            fcntl.lockf(fd, fcntl.LOCK_UN)
            os.unlink(file_name)


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
    config = BibOSConfig()
    data = config.get_data()

    admin_url = data['admin_url']
    xml_rpc_url = data.get('xml_rpc_url', '/admin-xml/')
    uid = data['uid']

    admin = BibOSAdmin(urlparse.urljoin(admin_url, xml_rpc_url))

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
        print >> sys.stderr, 'Error:', str(e)
        sys.exit(1)


def upload_dist_packages():
    config = BibOSConfig()
    data = config.get_data()

    admin_url = data['admin_url']
    xml_rpc_url = data.get('xml_rpc_url', '/admin-xml/')
    distribution = data['distribution']

    admin = BibOSAdmin(urlparse.urljoin(admin_url, xml_rpc_url))

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
        print >> sys.stderr, 'Error:', str(e)
        sys.exit(1)
