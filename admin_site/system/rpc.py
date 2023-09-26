# This module contains the implementation of the XML-RPC API used by the
# client.

import system.utils
import hashlib
import logging
from datetime import datetime
from dateutil import parser

from django.db.models import Q

from system.models import PC, Site, Configuration, ConfigurationEntry
from system.models import Job, SecurityProblem, SecurityEvent
from system.models import Citizen

from system.utils import get_citizen_login_validator

logger = logging.getLogger(__name__)


def register_new_computer(mac, name, distribution, site, configuration):
    """Register a new computer with the admin system - after registration, the
    computer will be submitted for approval."""

    # Hash our uid
    uid = hashlib.md5(mac.encode("utf-8")).hexdigest()

    if PC.objects.filter(uid=uid).count():
        raise Exception(
            "This computer is already registered with the chosen admin portal. "
            "Start by deleting the computer on the computer list on your site "
            "and then restart the registration."
        )
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

    # Update configuration with os2 product
    # New image versions set it themselves, old don't so for those
    # we detect and set it this way
    if "os2_product" not in configuration:
        if "os2borgerpc_version" in configuration:
            product = "os2borgerpc"
        else:
            product = "os2borgerpc kiosk"
        configuration.update({"os2_product": product})

    # remove mac and uid from the configuration
    # We don't need them saved as both attributes and configuration entries
    try:
        del configuration["mac"]
        del configuration["uid"]
    except KeyError:
        pass

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
            # Empty strings might be sent in rare cases, which otherwise cause validation errors
            if jd["started"]:
                job.started = jd["started"]
            if jd["finished"]:
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

    try:
        pc = PC.objects.get(uid=pc_uid)
    except PC.DoesNotExist:
        raise Exception(
            "This Computer does not appear to be registered with the configured admin portal."
        )

    pc.last_seen = datetime.now()
    pc.save()

    if not pc.is_activated:
        # Fail silently
        return {}

    jobs = []
    for job in pc.jobs.filter(status=Job.NEW).order_by("pk"):
        job.status = Job.SUBMITTED
        job.save()
        jobs.append(job.as_instruction)

    # Check for security scripts covering the site and
    # security scripts covering groups the pc is a member of.
    security_problems = SecurityProblem.objects.filter(
        Q(site=pc.site, alert_groups__isnull=True)
        | Q(alert_groups__in=pc.pc_groups.all())
    ).select_related("security_script")

    scripts = []

    for security_problem in security_problems:
        # inject security problem uid into the script code.
        # "name" will be used as part of the script name on the client, whereas SECURITY_PROBLEM_UID is used internally to
        # pair SecurityProblems with SecurityEvents
        identifier = (
            f"script{security_problem.security_script.id}_problem{security_problem.id}"
        )
        script_dict = {
            "name": identifier,
            "executable_code": security_problem.security_script.executable_code.read()
            .decode("utf8")
            .replace("%SECURITY_PROBLEM_UID%", str(security_problem.id)),
        }
        scripts.append(script_dict)

    instructions = {
        "security_scripts": scripts,
        "jobs": jobs,
        "configuration": pc.get_full_config(),
    }

    return instructions


def push_config_keys(pc_uid, config_dict):
    try:
        pc = PC.objects.get(uid=pc_uid)
    except PC.DoesNotExist:
        raise Exception(
            "This Computer does not appear to be registered with the configured admin portal."
        )
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


# TODO: Log events for SecurityProblems that don't exist
# + events where the site's computer and rule's computer don't match
# TODO: If we update all clients and stop using complete_log just
# stop handling it here completely as it's null=True
def push_security_events(pc_uid, events_csv):
    pc = PC.objects.get(uid=pc_uid)

    for event in events_csv:
        try:
            event_date, rule_id, event_summary, event_complete_log = event.split(",")
        except ValueError:
            logger.exception(
                "Security event generated ValueError, Event: %s, PC UID: %s",
                event,
                pc.uid,
            )
            return 1

        try:
            security_problem = SecurityProblem.objects.filter(id=rule_id).first()
        except ValueError:
            logger.exception(
                "Security event log contained invalid rule ID %s, Event: %s, PC UID %s",
                rule_id,
                str(event),
                pc.uid,
            )
            continue

        if not security_problem:
            # Ignore ID's of SecurityProblems that don't exist
            logger.error(
                "Security problem with ID %s could not be found, Event: %s, PC UID %s",
                rule_id,
                str(event),
                pc.uid,
            )
            continue

        if not security_problem.site == pc.site:
            # Ignore SecurityProblems matching a computer on a different site
            logger.error(
                (
                    "Security problem with ID %s does not "
                    "match site of PC, Event: %s, PC UID %s"
                ),
                security_problem.id,
                str(event),
                pc.uid,
            )
            continue

        now = datetime.now()
        event_occurred_time_object = parser.parse(event_date)
        security_event = SecurityEvent.objects.create(
            problem=security_problem,
            pc=pc,
            occurred_time=event_occurred_time_object,
            reported_time=now,
            summary=event_summary,
        )

        # Notify subscribed users
        system.utils.notify_users(
            security_event,
            security_problem,
            pc,
        )

    return 0


def citizen_login(username, password, site, prevent_dual_login=False):
    """Check if user is allowed to log in and give the go-ahead if so.

    Return values:
        r < 0: User is quarantined and may login in -r minutes
        r = 0: Unable to authenticate.
        r > 0: The user is allowed r minutes of login time.
    """

    time_allowed = 0
    try:
        site = Site.objects.get(uid=site)
    except Site.DoesNotExist:
        logger.error(f"Site {site} does not exist - unable to proceed.")
        return time_allowed
    login_validator = get_citizen_login_validator()
    citizen_id = login_validator(username, password, site)
    citizen_hash = ""

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
            if now < quarantined_from and not citizen.logged_in:
                time_allowed = (
                    time_allowed
                    - (now - citizen.last_successful_login).total_seconds() // 60
                )
                if prevent_dual_login:
                    citizen.logged_in = True
            elif now < quarantined_from and citizen.logged_in:
                citizen_hash = "logged_in"
            elif (now - quarantined_from) >= quarantine_duration:
                citizen.last_successful_login = now
                if prevent_dual_login:
                    citizen.logged_in = True
            else:
                # (now - quarantined_from) < quarantine_duration:
                time_allowed = (
                    (now - quarantined_from).total_seconds()
                    - quarantine_duration.total_seconds()
                ) // 60
        else:
            # First-time login, all good.
            citizen = Citizen(
                citizen_id=citizen_hash,
                last_successful_login=now,
                site=site,
                logged_in=True,
            )
        citizen.save()

    if prevent_dual_login:
        return int(time_allowed), citizen_hash
    else:
        return int(time_allowed)


def citizen_logout(citizen_hash):
    try:
        citizen = Citizen.objects.get(citizen_id=citizen_hash)
        citizen.logged_in = False
        citizen.save()
        return 0
    except Citizen.DoesNotExist:
        return 1
