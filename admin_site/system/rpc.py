# This module contains the implementation of the XML-RPC API used by the
# client.

import system.utils
import hashlib
import logging
from datetime import datetime
from dateutil import parser

from django.conf import settings
from django.db.models import Q

from system.models import PC, Site, Configuration, ConfigurationEntry
from system.models import Job, SecurityProblem, SecurityEvent
from system.models import Citizen, LoginLog

from system.utils import (
    get_citizen_login_api_validator,
    easy_appointments_booking_validate,
    send_password_sms,
)

logger = logging.getLogger(__name__)


def register_new_computer_v2(mac, name, site, configuration):
    """Register a new computer with the admin system - after registration, the
    computer will be submitted for approval."""

    # Hash our uid
    uid = hashlib.md5(mac.encode("utf-8")).hexdigest()

    if PC.objects.filter(uid=uid).count():
        name = PC.objects.get(uid=uid).name
        raise Exception(
            "A computer with the same MAC address as this computer is already "
            f"registered with the chosen admin portal under the name {name}. "
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


# TODO: Backwards compatible function. Delete once there are no longer active clients calling it.
def register_new_computer(mac, name, distribution, site, configuration):
    return register_new_computer_v2(mac, name, site, configuration)


def send_status_info_v2(pc_uid, job_data):
    """Update the status of outstanding jobs.
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

    pc.save()

    return 0


# TODO: Backwards compatible function. Delete once there are no longer active clients calling it.
def send_status_info(pc_uid, package_data, job_data, update_required):
    return send_status_info_v2(pc_uid, job_data)


def get_instructions(pc_uid):
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
        event_split = event.split(",")
        if len(event_split) == 3 or len(event_split) == 4:
            event_date = event_split[0]
            rule_id = event_split[1]
            event_summary = event_split[2]
        else:
            if settings.DEBUG or "test" in settings.SERVER_EMAIL:
                logger.exception(
                    "Invalid security event format with %s elements, Event: %s, PC UID: %s,",
                    len(event_split),
                    event,
                    pc.uid,
                )
            continue

        try:
            security_problem = SecurityProblem.objects.filter(id=rule_id).first()
        except ValueError:
            if settings.DEBUG or "test" in settings.SERVER_EMAIL:
                logger.exception(
                    "Security event log contained invalid rule ID %s, Event: %s, PC UID %s",
                    rule_id,
                    str(event),
                    pc.uid,
                )
            continue

        if not security_problem:
            # Ignore ID's of SecurityProblems that don't exist
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


def sms_login(phone_number, message, pc_uid, require_booking=False, pc_name=None):
    """Check if the user is allowed to log in and if so, send a sms with
    the required password to the entered phone number.
    Whether a user is allowed to log in is determined by checking for a
    matching booking if booking is required or by checking the Citizen
    quarantine logic if booking is not required.

    The phone number given to this function should include the
    country code.

    Return values:
        time < 0: User is quarantined and may login in -r minutes or
                  their next booking starts in -r minutes.
        time = 0: Unable to authenticate.
        time > 0: The user is allowed r minutes of login time.
        citizen_hash: If booking is not required and the user is allowed
                      to log in, this will be the hashed version of their
                      phone number.
        Other possible values include:
        citizen_hash = '': No special errors and booking is required.
        citizen_hash = 'no_booking': No matching or future booking found.
        citizen_hash = 'logged_in': The user is already logged in on
                        another machine. This value is only used when
                        booking is NOT required.
        citizen_hash = 'sms_failed': Failed to authenticate with sms API."""
    citizen_hash = ""
    try:
        pc = PC.objects.get(uid=pc_uid)
        if not pc.is_activated:
            # Fail silently
            return int(0), citizen_hash
        site = pc.site
    except PC.DoesNotExist:
        # The function is ultimately supposed to exit here, but for the sake of backwards
        # compatibility, we initially handle the old version
        site_uid = pc_uid
        try:
            site = Site.objects.get(uid=site_uid)
        except Site.DoesNotExist:
            logger.error(f"Site {site_uid} does not exist - unable to proceed.")
            return int(0), citizen_hash

    now = datetime.now()
    # If booking is required then the bookings determine when and how long the
    # users can log in
    if require_booking:
        date_time = now.strftime("%Y-%m-%d %H:%M:%S")
        # Check for a matching booking
        booking_time, later_booking = easy_appointments_booking_validate(
            phone_number, date_time, site, pc_name
        )
        if booking_time:  # If a matching booking was found
            time_allowed = (
                datetime.strptime(booking_time, "%Y-%m-%d %H:%M:%S") - now
            ).total_seconds() // 60
            if later_booking:  # If the matching booking starts later in the day
                time_allowed = -time_allowed
        else:
            # booking_time will be None if no matching booking was found and
            # 0 if the API validation failed
            if booking_time is None:
                citizen_hash = "no_booking"
            return int(0), citizen_hash
    # If booking is not required, use the standard quarantine system.
    # Don't update last_successful_login and logged_in until the
    # citizen actually logs in (sms_login_finalize)
    else:
        citizen_hash = hashlib.sha512(str(phone_number[-8:]).encode()).hexdigest()
        # Get previous login, if any.
        try:
            citizen = Citizen.objects.get(citizen_id=citizen_hash)
        except Citizen.DoesNotExist:
            citizen = None

        time_allowed = site.user_login_duration.total_seconds() // 60

        if citizen:
            quarantine_duration = site.user_quarantine_duration
            quarantined_from = citizen.last_successful_login + site.user_login_duration
            if now < quarantined_from and not citizen.logged_in:
                time_allowed = (
                    time_allowed
                    - (now - citizen.last_successful_login).total_seconds() // 60
                )
            elif now < quarantined_from and citizen.logged_in:
                citizen_hash = "logged_in"
            elif (now - quarantined_from) < quarantine_duration:
                time_allowed = (
                    (now - quarantined_from).total_seconds()
                    - quarantine_duration.total_seconds()
                ) // 60

    # Only send a sms if they are allowed to log in
    if time_allowed > 0:
        sms_sent = send_password_sms(phone_number, message, site)

        if not sms_sent:
            citizen_hash = "sms_failed"

    return int(time_allowed), citizen_hash


def sms_login_finalize(phone_number, pc_uid, require_booking, save_log):
    """Finalize the sms_login-process by creating a LoginLog object if
    required and/or updating the relevant Citizen object if booking
    is not required.

    The phone number given to this function should NOT include the
    country code.

    Return values:
        log_id = '': Writing a log is not required.
        log_id = int: If a log should be written, this will be the id
                      of the created log object. It is used to update
                      the logout time later."""
    try:
        pc = PC.objects.get(uid=pc_uid)
        if not pc.is_activated:
            # Fail silently
            return 0
        site = pc.site
    except PC.DoesNotExist:
        # The function is ultimately supposed to exit here, but for the sake of backwards
        # compatibility, we initially handle the old version
        site_uid = pc_uid
        try:
            site = Site.objects.get(uid=site_uid)
        except Site.DoesNotExist:
            logger.error(f"Site {site_uid} does not exist - unable to proceed.")
            return 0
    # If booking is not required, we use the standard quarantine system
    # time_allowed has already been checked by sms_login, so we only need
    # to update last_successful_login and/or logged_in
    if not require_booking:
        citizen_hash = hashlib.sha512(str(phone_number[-8:]).encode()).hexdigest()
        now = datetime.now()
        try:
            citizen = Citizen.objects.get(citizen_id=citizen_hash)
        except Citizen.DoesNotExist:
            citizen = None
        if citizen:
            quarantine_duration = site.user_quarantine_duration
            quarantined_from = citizen.last_successful_login + site.user_login_duration
            if now < quarantined_from and not citizen.logged_in:
                citizen.logged_in = True
            elif (now - quarantined_from) >= quarantine_duration:
                citizen.last_successful_login = now
                citizen.logged_in = True
        else:
            # First-time login, all good.
            citizen = Citizen(
                citizen_id=citizen_hash,
                last_successful_login=now,
                site=site,
                logged_in=True,
            )
        citizen.save()

    log_id = ""
    if save_log:
        now = datetime.now()
        # Initially, logout_time = login_time
        login_log = LoginLog(
            identifier=phone_number,
            site=site,
            date=datetime.date(now),
            login_time=datetime.time(now),
            logout_time=datetime.time(now),
        )
        login_log.save()
        log_id = login_log.id

    return log_id


def sms_logout(citizen_hash, log_id):
    """Update the logout time of the relevant LoginLog object if
    required and/or log out the relevant Citizen object if
    booking is not required."""

    if log_id:
        try:
            # Update logout_time
            login_log = LoginLog.objects.get(id=log_id)
            now = datetime.now()
            login_log.logout_time = datetime.time(now)
            login_log.save()
        except LoginLog.DoesNotExist:
            pass
    if citizen_hash:
        try:
            citizen = Citizen.objects.get(citizen_id=citizen_hash)
            citizen.logged_in = False
            citizen.save()
        except Citizen.DoesNotExist:
            pass
    return 0


def citizen_login(username, password, pc_uid, prevent_dual_login=False):
    """Check if user is allowed to log in and give the go-ahead if so.

    Return values:
        r < 0: User is quarantined and may login in -r minutes
        r = 0: Unable to authenticate.
        r > 0: The user is allowed r minutes of login time.
    """

    time_allowed = 0
    try:
        pc = PC.objects.get(uid=pc_uid)
        if not pc.is_activated:
            # Fail silently
            return time_allowed
        site = pc.site
    except PC.DoesNotExist:
        # The function is ultimately supposed to exit here, but for the sake of backwards
        # compatibility, we initially handle the old version
        site_uid = pc_uid
        try:
            site = Site.objects.get(uid=site_uid)
        except Site.DoesNotExist:
            logger.error(f"Site {site_uid} does not exist - unable to proceed.")
            return time_allowed
    login_validator = get_citizen_login_api_validator()
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
