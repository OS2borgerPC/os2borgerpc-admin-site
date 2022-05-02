# This module contains the implementation of the XML-RPC API used by the
# client.

import system.proxyconf
import system.utils
import hashlib
import logging

from datetime import datetime

from .models import PC, Site, Configuration, ConfigurationEntry
from .models import Job, Script, SecurityProblem, SecurityEvent
from .models import Citizen

from .utils import get_citizen_login_validator


def register_new_computer(mac, name, distribution, site, configuration):
    """Register a new computer with the admin system - after registration, the
    computer will be submitted for approval."""

    # Hash our uid
    uid = hashlib.md5(mac.encode("utf-8")).hexdigest()

    try:
        new_pc = PC.objects.get(uid=uid)
    except PC.DoesNotExist:
        new_pc = PC(name=name, uid=uid)
        new_pc.site = Site.objects.get(uid=site)

    new_pc.is_activated = False
    new_pc.mac = mac
    # Create new configuration, populate with data from computer's config.
    # If a configuration with the same ID is hanging, reuse.
    config_name = "_".join([site, name, uid])
    try:
        my_config = Configuration.objects.get(name=config_name)
    except Configuration.DoesNotExist:
        my_config = Configuration()
        my_config.name = config_name
    finally:
        # Delete pre-existing entries
        entries = ConfigurationEntry.objects.filter(owner_configuration=my_config)
        for e in entries:
            e.delete()
    my_config.save()
    # And load configuration

    # Update configuration with uid
    configuration.update({"uid": uid})

    # Update configuration with os2 product
    # New image versions set it themselves, old don't so for those
    # we detect and set it this way
    if "os2_product" not in configuration:
        if "os2borgerpc_version" in configuration:
            product = "os2borgerpc"
        else:
            product = "os2borgerpc kiosk"
        configuration.update({"os2_product": product})

    for k, v in list(configuration.items()):
        entry = ConfigurationEntry(key=k, value=v, owner_configuration=my_config)
        entry.save()
    # Set and save PmC
    new_pc.configuration = my_config
    new_pc.save()
    return uid


def upload_dist_packages(distribution_uid, package_data):
    """This will upload the packages and package versions for a given
    BibOS distribution.
    This is depreacated and will be removed when we can."""
    # Phased out - we keep this for backwards compliance only.
    return 0


def send_status_info(pc_uid, package_data, job_data, update_required):
    """Update the status of outstanding jobs and (now deprecated) package data.
    If no updates, these will be None. In that
    case, this function really works as an "I'm alive" signal."""

    # TODO: Code this

    # 1. Lookup PC, update "last_seen" field
    pc = PC.objects.get(uid=pc_uid)

    if not pc.is_activated:
        # Fail silently
        return 0

    pc.last_seen = datetime.now()
    pc.save()

    # 2. Update jobs with job data
    if job_data is not None:
        for jd in job_data:
            job = Job.objects.filter(pk=jd["id"]).first()
            if not job:
                continue
            job.status = jd["status"]
            job.started = jd["started"]
            job.finished = jd["finished"]
            job.log_output = jd["log_output"]
            job.save()

    # 3. Check if update is required.
    if update_required is not None:
        updates, security_updates = list(map(int, update_required))
        # Save update info in configuration
        pc.configuration.update_entry("updates", updates)
        pc.configuration.update_entry("security_updates", security_updates)

    pc.save()

    return 0


def get_instructions(pc_uid, update_data=None):
    """This function will ask for new instructions in the form of a list of
    jobs, which will be scheduled for execution and executed upon receipt.
    These jobs will generally take the form of bash scripts."""

    pc = PC.objects.get(uid=pc_uid)

    pc.last_seen = datetime.now()
    pc.save()

    if not pc.is_activated:
        # Fail silently
        return ([], False)

    jobs = []
    for job in pc.jobs.filter(status=Job.NEW).order_by("pk"):
        job.status = Job.SUBMITTED
        job.save()
        jobs.append(job.as_instruction)

    security_objects = []
    # First check for security scripts covering the site
    site_security_problems = SecurityProblem.objects.filter(site_id=pc.site).exclude(
        alert_groups__isnull=False
    )

    for security_problem in site_security_problems:
        security_objects.append(insert_security_problem_uid(security_problem))

    # Then check for security scripts covering groups the pc is a member of.
    pc_groups = pc.pc_groups.all()
    if len(pc_groups) > 0:

        for group in pc_groups:
            security_problems = SecurityProblem.objects.filter(alert_groups=group.id)
            if len(security_problems) > 0:
                for problem in security_problems:
                    security_objects.append(insert_security_problem_uid(problem))

    scripts = []

    for script in security_objects:
        if script["is_security_script"] == 1:
            s = {"name": script["name"], "executable_code": script["executable_code"]}
            scripts.append(s)

    result = {
        "security_scripts": scripts,
        "jobs": jobs,
        "configuration": pc.get_full_config(),
    }

    return result


def insert_security_problem_uid(securityproblem):
    script = Script.objects.get(security_problems=securityproblem)
    code = script.executable_code.read().decode("utf8")
    code = str(code).replace("%SECURITY_PROBLEM_UID%", securityproblem.uid)
    s = {
        "name": securityproblem.uid,
        "executable_code": code,
        "is_security_script": script.is_security_script,
    }
    return s


def get_proxy_setup(pc_uid):
    pc = PC.objects.get(uid=pc_uid)
    if not pc.is_activated:
        return 0
    return system.proxyconf.get_proxy_setup(pc_uid)


def push_config_keys(pc_uid, config_dict):
    pc = PC.objects.get(uid=pc_uid)
    if not pc.is_activated:
        return 0

    # We need two config dicts: one from the PC itself and one from groups
    # and global configuration
    config_lists = pc.get_list_of_configurations()

    pc_config_list = config_lists.pop()

    pc_config = {}
    for entry in pc_config_list.entries.all():
        pc_config[entry.key] = entry.value

    others_config = {}
    for conf in config_lists:
        for entry in conf.entries.all():
            others_config[entry.key] = entry.value

    for key, value in list(config_dict.items()):
        # Special case: If the value we want is in others_config, we just have
        # to remove any pc-specific config:
        if key in others_config and others_config[key] == value:
            if key in pc_config:
                pc.configuration.remove_entry(key)
        else:
            pc.configuration.update_entry(key, value)

    return True


def push_security_events(pc_uid, csv_data):
    pc = PC.objects.get(uid=pc_uid)

    for data in csv_data:
        csv_split = data.split(",")
        try:
            security_problem = SecurityProblem.objects.get(uid=csv_split[1])

            new_security_event = SecurityEvent(problem=security_problem, pc=pc)
            new_security_event.occurred_time = datetime.strptime(
                csv_split[0], "%Y%m%d%H%M"
            )
            new_security_event.reported_time = datetime.now()
            new_security_event.summary = csv_split[2]
            new_security_event.complete_log = csv_split[3]
            new_security_event.save()
        except IndexError:
            return 1

        # Notify subscribed users
        system.utils.notify_users(csv_split, security_problem, pc)

    return 0


def citizen_login(username, password, site):
    """Check if user is allowed to log in and give the go-ahead if so.

    Return values:
        r < 0: User is quarantined and may login in -r minutes
        r = 0: Unable to authenticate.
        r > 0: The user is allowed r minutes of login time.
    """

    logger = logging.getLogger(__name__)
    time_allowed = 0
    try:
        site = Site.objects.get(uid=site)
    except Site.DoesNotExist:
        logger.error(f"Site {site} does not exist - unable to proceed.")
        return time_allowed
    login_validator = get_citizen_login_validator()
    citizen_id = login_validator(username, password, site.isil)

    if citizen_id:
        citizen_hash = hashlib.sha512(str(citizen_id).encode()).hexdigest()
        now = datetime.now()
        # Time in minutes.
        time_allowed = site.user_login_duration.total_seconds() // 60
        # Get previous login, if any.
        try:
            citizen = Citizen.objects.get(citizen_id=citizen_hash)
        except Citizen.DoesNotExist:
            citizen = None

        if citizen:
            quarantine_duration = site.user_quarantine_duration
            quarantined_from = citizen.last_successful_login + site.user_login_duration
            if now < quarantined_from:
                time_allowed = (
                    time_allowed
                    - (now - citizen.last_successful_login).total_seconds() // 60
                )
            elif (now - quarantined_from) >= quarantine_duration:
                citizen.last_successful_login = now
                citizen.save()
            else:
                # (now - quarantined_from) < quarantine_duration:
                time_allowed = (
                    (now - quarantined_from).total_seconds()
                    - quarantine_duration.total_seconds()
                ) // 60
        else:
            # First-time login, all good.
            citizen = Citizen(
                citizen_id=citizen_hash, last_successful_login=now, site=site
            )
        citizen.save()

    return int(time_allowed)
