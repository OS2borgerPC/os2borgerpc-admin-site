# This module contains the implementation of the XML-RPC API used by the
# client.

import system.utils
import hashlib
import hmac
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Q

from system.models import PC, Site, Configuration, ConfigurationEntry
from system.models import Job, SecurityProblem, SecurityEvent
from system.models import Citizen, LoginLog

from system.utils import (
    get_citizen_login_api_validator,
    easy_appointments_booking_validate,
    send_password_sms,
    quria_login_validate,
)

logger = logging.getLogger(__name__)

CLIENT_KEY_EXPECTED_LEN = 64
CLIENT_KEY_ALLOWED_MODES = {"off", "migration", "on"}

# Governing/trust config keys marked read_only in the admin portal UI at
# registration, so they cannot be edited or deleted through the portal (see
# Configuration.update_from_request). Wiping admin_url via a config delete makes
# a machine unreachable, so protecting these prevents that "bricking".
#
# This is the same canonical control-plane set the client-push protection uses
# (push_config_keys); keep the two in sync. It deliberately does NOT include the
# inventory/telemetry keys that Magenta also marks read_only - those
# are not security-critical and marking them would only take away the admin's
# ability to edit them in the UI. Add them here if UI parity is wanted.
READ_ONLY_IN_UI_CONFIG_KEYS = frozenset(
    {
        "admin_url",
        "xml_rpc_url",
        "os2borgerpc_client_package",
        "os2borgerpc_client_version",
    }
)

def _client_key_mode():
    mode = getattr(settings, "CLIENT_KEY_AUTH_MODE", None)
    if mode is None:
        mode = "on" if getattr(settings, "REQUIRE_CLIENT_KEY", False) else "off"
    mode = str(mode).strip().lower()
    if mode not in CLIENT_KEY_ALLOWED_MODES:
        logger.warning(
            "Invalid CLIENT_KEY_AUTH_MODE '%s'. Falling back to 'off'.",
            mode,
        )
        return "off"
    return mode


def _normalize_client_key(client_key):
    if client_key is None:
        return None
    if not isinstance(client_key, str):
        raise Exception("Client key authentication failed: malformed client_key value.")
    value = client_key.strip().lower()
    if not value:
        return None
    if len(value) != CLIENT_KEY_EXPECTED_LEN:
        raise Exception("Client key authentication failed: malformed client_key length.")
    if any(c not in "0123456789abcdef" for c in value):
        raise Exception("Client key authentication failed: malformed client_key format.")
    return value


def _hash_client_key(normalized_client_key):
    if not normalized_client_key:
        return None
    return hashlib.sha256(normalized_client_key.encode("ascii")).hexdigest()


def _client_key_present(client_key):
    return client_key is not None and bool(str(client_key).strip())


def _log_client_key_auth(
    method_name,
    key_present,
    key_match,
    machine_identifier=None,
    rejection_reason=None,
):
    logger.info(
        "client_key_auth method=%s machine=%s key_present=%s key_match=%s rejection_reason=%s",
        method_name,
        machine_identifier,
        bool(key_present),
        key_match,
        rejection_reason,
    )


def _store_or_rotate_pc_client_key(pc, normalized_client_key, method_name):
    if normalized_client_key is None:
        _log_client_key_auth(
            method_name,
            key_present=False,
            key_match=None,
            machine_identifier=pc.uid,
            rejection_reason=None,
        )
        return False

    incoming_hash = _hash_client_key(normalized_client_key)
    if not pc.client_key_hash:
        pc.client_key_hash = incoming_hash
        pc.save(update_fields=["client_key_hash"])
        _log_client_key_auth(
            method_name,
            key_present=True,
            key_match=True,
            machine_identifier=pc.uid,
            rejection_reason=None,
        )
        return True

    if hmac.compare_digest(pc.client_key_hash, incoming_hash):
        _log_client_key_auth(
            method_name,
            key_present=True,
            key_match=True,
            machine_identifier=pc.uid,
            rejection_reason=None,
        )
        return False

    # Transitional policy: allow and rotate key with audit log.
    old_hash = pc.client_key_hash
    pc.client_key_hash = incoming_hash
    pc.save(update_fields=["client_key_hash"])
    logger.warning(
        "client_key_auth_transitional_rotate method=%s machine=%s old_hash_prefix=%s new_hash_prefix=%s",
        method_name,
        pc.uid,
        old_hash[:12],
        incoming_hash[:12],
    )
    _log_client_key_auth(
        method_name,
        key_present=True,
        key_match=False,
        machine_identifier=pc.uid,
        rejection_reason="rotated_transitional",
    )
    return True


def _enforce_client_key_for_pc(method_name, pc, client_key):
    mode = _client_key_mode()
    normalized_client_key = _normalize_client_key(client_key)
    incoming_hash = _hash_client_key(normalized_client_key)
    stored_hash = pc.client_key_hash
    key_present = normalized_client_key is not None

    if mode == "off":
        if stored_hash and incoming_hash:
            key_match = hmac.compare_digest(stored_hash, incoming_hash)
        else:
            key_match = None
        _log_client_key_auth(
            method_name,
            key_present=key_present,
            key_match=key_match,
            machine_identifier=pc.uid,
            rejection_reason=None,
        )
        if not stored_hash and normalized_client_key:
            pc.client_key_hash = incoming_hash
            pc.save(update_fields=["client_key_hash"])
        return

    if mode == "on" and not key_present:
        _log_client_key_auth(
            method_name,
            key_present=False,
            key_match=False,
            machine_identifier=pc.uid,
            rejection_reason="missing_client_key",
        )
        raise Exception("Client key authentication failed: missing client_key.")

    if not stored_hash:
        if key_present:
            pc.client_key_hash = incoming_hash
            pc.save(update_fields=["client_key_hash"])
            _log_client_key_auth(
                method_name,
                key_present=True,
                key_match=True,
                machine_identifier=pc.uid,
                rejection_reason="stored_new_key",
            )
            return

        if mode == "migration":
            _log_client_key_auth(
                method_name,
                key_present=False,
                key_match=None,
                machine_identifier=pc.uid,
                rejection_reason="legacy_machine_without_key",
            )
            return

        _log_client_key_auth(
            method_name,
            key_present=False,
            key_match=False,
            machine_identifier=pc.uid,
            rejection_reason="no_stored_key_and_missing_client_key",
        )
        raise Exception(
            "Client key authentication failed: machine has no registered key and request did not provide one."
        )

    if not key_present:
        _log_client_key_auth(
            method_name,
            key_present=False,
            key_match=False,
            machine_identifier=pc.uid,
            rejection_reason="missing_client_key",
        )
        raise Exception("Client key authentication failed: missing client_key.")

    if not hmac.compare_digest(stored_hash, incoming_hash):
        _log_client_key_auth(
            method_name,
            key_present=True,
            key_match=False,
            machine_identifier=pc.uid,
            rejection_reason="mismatched_client_key",
        )
        raise Exception("Client key authentication failed: mismatched client_key.")

    _log_client_key_auth(
        method_name,
        key_present=True,
        key_match=True,
        machine_identifier=pc.uid,
        rejection_reason=None,
    )


def _log_missing_machine_mapping_for_client_key(method_name, client_key):
    _normalize_client_key(client_key)
    key_present = _client_key_present(client_key)
    _log_client_key_auth(
        method_name,
        key_present=key_present,
        key_match=None,
        machine_identifier=None,
        rejection_reason="machine_mapping_unavailable_fallback_allowed",
    )


def register_new_computer_v2(mac, name, site, configuration, client_key=None):
    """Register a new computer with the admin system - after registration, the
    computer will be submitted for approval."""

    # Hash our uid
    uid = hashlib.md5(mac.encode("utf-8")).hexdigest()

    normalized_client_key = _normalize_client_key(client_key)

    if PC.objects.filter(uid=uid).count():
        existing_pc = PC.objects.get(uid=uid)
        _store_or_rotate_pc_client_key(
            existing_pc,
            normalized_client_key,
            method_name="register_new_computer_v2",
        )
        name = existing_pc.name
        raise Exception(
            "A computer with the same MAC address as this computer is already "
            f"registered with the chosen admin portal under the name {name}. "
            "Start by deleting the computer on the computer list on your site "
            "and then restart the registration."
        )
    # If we are here then no matching PC object exists
    new_pc = PC(name=name, uid=uid)
    try:
        new_pc.site = Site.objects.get(uid=site)
    except Site.DoesNotExist:
        raise Exception(
            "The chosen site UID does not match any sites on the "
            "chosen admin portal."
        )

    new_pc.is_activated = False
    new_pc.mac = mac
    if normalized_client_key:
        new_pc.client_key_hash = _hash_client_key(normalized_client_key)
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
        entry = ConfigurationEntry(
            key=k,
            value=v,
            read_only=k in READ_ONLY_IN_UI_CONFIG_KEYS,
            owner_configuration=my_config,
        )
        entry.save()
    # Set and save PmC
    new_pc.configuration = my_config
    new_pc.save()
    return uid


# TODO: Backwards compatible function. Delete once there are no longer active clients calling it.
def register_new_computer(
    mac, name, distribution, site, configuration, client_key=None
):
    return register_new_computer_v2(mac, name, site, configuration, client_key)


def send_status_info_v2(pc_uid, job_data, client_key=None):
    """Update the status of outstanding jobs.
    If no updates, these will be None. In that
    case, this function really works as an "I'm alive" signal."""

    # 1. Lookup PC, update "last_seen" field
    pc = PC.objects.get(uid=pc_uid)
    _enforce_client_key_for_pc("send_status_info_v2", pc, client_key)

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
def send_status_info(
    pc_uid, package_data, job_data, update_required=None, client_key=None
):
    return send_status_info_v2(pc_uid, job_data, client_key)


def get_instructions(pc_uid, client_key=None):
    """This function will ask for new instructions in the form of a list of
    jobs, which will be scheduled for execution and executed upon receipt.
    These jobs will generally take the form of bash scripts."""

    try:
        pc = PC.objects.get(uid=pc_uid)
    except PC.DoesNotExist:
        raise Exception(
            "This Computer does not appear to be registered with the configured admin portal."
        )

    _enforce_client_key_for_pc("get_instructions", pc, client_key)

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


# Configuration keys the client-facing API must never allow a client to set.
# These are "control-plane" values: they decide which server the client trusts
# (admin_url, xml_rpc_url), what code it installs and runs as root
# (os2borgerpc_client_package, os2borgerpc_client_version), or the client's own
# identity (uid, mac, site). All of them are either server-authoritative or
# set once at install time; a genuine client never needs to push them upwards.
#
# get_instructions() hands whatever is stored here straight back to the client
# via get_full_config(), which then writes it to its local config. Because the
# client-api is unauthenticated (identity is only md5(MAC), which is public),
# letting a caller set these turns push_config_keys into remote re-homing and
# remote code execution as root.
#
# NOTE: this is a denylist of the *closed* set of control-plane keys, on
# purpose - ordinary telemetry and script-defined keys are meant to be pushed
# freely. If a future config key ever gains trust or code-execution semantics,
# it MUST be added here.
CLIENT_IMMUTABLE_CONFIG_KEYS = frozenset(
    {
        "admin_url",
        "xml_rpc_url",
        "os2borgerpc_client_package",
        "os2borgerpc_client_version",
        "uid",
        "mac",
        "site",
    }
)


def push_config_keys(pc_uid, config_dict, client_key=None):
    try:
        pc = PC.objects.get(uid=pc_uid)
    except PC.DoesNotExist:
        raise Exception(
            "This Computer does not appear to be registered with the configured admin portal."
        )
    _enforce_client_key_for_pc("push_config_keys", pc, client_key)
    if not pc.is_activated:
        return 0

    # Drop any attempt to set a protected control-plane key, and log it. We
    # drop the individual keys rather than reject the whole call, so a batch
    # that legitimately mixes ordinary keys with a protected one still applies
    # the ordinary ones. A logged line here is also a detection signal.
    protected = CLIENT_IMMUTABLE_CONFIG_KEYS.intersection(config_dict)
    if protected:
        logger.warning(
            "push_config_keys: refused attempt to set protected key(s) %s "
            "on PC '%s' (uid %s)",
            sorted(protected),
            pc.name,
            pc_uid,
        )
        config_dict = {
            k: v for k, v in config_dict.items() if k not in protected
        }

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
def push_security_events(pc_uid, events_csv, client_key=None):
    pc = PC.objects.get(uid=pc_uid)
    _enforce_client_key_for_pc("push_security_events", pc, client_key)

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
        event_occurred_time_object = datetime.strptime(event_date, "%Y%m%d%H%M%S")
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


def general_citizen_login(pc_uid, integration, value_dict, client_key=None):
    """Check if the user is allowed to log in by validating
    their login via the indicated login integration.

    Return values:
        time < 0: User is quarantined and may login in -r minutes or
                  the next booking (theirs or anothers) starts in -r
                  minutes.
        time = 0: Unable to authenticate.
        time > 0: The user is allowed r minutes of login time.
        citizen_hash: If booking is not required or idle logins are
                      allowed and the user is allowed
                      to log in, this will be the hashed version of their
                      identifier (e.g. loaner number).
        Other possible values include:
        citizen_hash = '': No special errors and booking is required.
        citizen_hash = 'blocked': The user credentials were correct, but
                       the user is blocked in the relevant system (Quria)
        citizen_hash = 'no_booking': No matching or future booking found.
        citizen_hash = 'logged_in': The user is already logged in on
                        another machine. This value is only used when
                        booking is NOT required or idle logins are
                        allowed.
        citizen_hash = 'quarantine' : Idle logins are allowed, but the
                       user is quarantined and does not have an active
                       booking or a future booking that starts before
                       the end of the quarantine.
        citizen_hash = 'booked' : Idle logins are allowed, but the
                       computer is currently booked by someone else.
        citizen_hash = 'later_booking' : The user cannot log in now,
                       but they have a booking that starts later.
        citizen_hash = 'booking_soon' : Idle logins are allowed, but
                       a future booking starts too soon for an idle
                       login to be possible.
        log_id : If a LoginLog was saved, this is the id of that object.
                 It is used to update the logout time durin logout.
                 If no LoginLog was saved, it will be an empty string."""
    citizen_hash = ""
    log_id = ""
    time_allowed = 0
    is_sms_booking = False
    try:
        pc = PC.objects.get(uid=pc_uid)
        _enforce_client_key_for_pc("general_citizen_login", pc, client_key)
        if not pc.is_activated:
            # Fail silently
            return int(time_allowed), citizen_hash, log_id
        site = pc.site
    except PC.DoesNotExist:
        logger.error(f"PC {pc_uid} does not exist - unable to proceed.")
        return int(time_allowed), citizen_hash, log_id

    # Start by validating the credentials to obtain the citizen_hash, which
    # is required for the Citizen quarantine system.
    if integration == "quria":
        loaner_number = value_dict["citizen_identifier"]
        pincode = value_dict["pincode"]
        status = quria_login_validate(site, loaner_number, pincode)
        if status == 2:  # Patron exists and is not blocked
            citizen_hash = hashlib.sha512(str(loaner_number).encode()).hexdigest()
        elif status == 1:  # Patron exists but is blocked
            return int(time_allowed), "blocked", log_id
        else:  # Invalid loaner number or pincode
            return int(time_allowed), citizen_hash, log_id

    # Determine if a custom login_duration and/or quarantine_duration is being used
    if "login_duration" in value_dict:
        login_duration = timedelta(minutes=value_dict["login_duration"])
    else:
        login_duration = site.user_login_duration
    if "quarantine_duration" in value_dict:
        quarantine_duration = timedelta(minutes=value_dict["quarantine_duration"])
    else:
        quarantine_duration = site.user_quarantine_duration

    now = datetime.now()
    # If booking is required then the bookings determine when and how long the
    # users can log in
    if "require_booking" in value_dict:
        logged_in = False
        # If idle logins are allowed, the user can log in without a booking
        # if their remaining login duration is less than the time until the
        # next booking starts. The Citizen quarantine system also governs
        # these idle logins
        if "allow_idle_login" in value_dict:
            try:
                citizen = Citizen.objects.get(citizen_id=citizen_hash)
            except Citizen.DoesNotExist:
                citizen = None
            if citizen:
                quarantined_from = citizen.last_successful_login + login_duration
                if (
                    citizen.logged_in
                    and not quarantined_from + quarantine_duration < now
                ):
                    # If the citizen is currently logged in on another computer,
                    # idle login should not be allowed
                    quarantined_from = None
                    logged_in = True
            else:
                quarantined_from = False
        else:
            quarantined_from = None
        # Check the booking system
        time_allowed, note = easy_appointments_booking_validate(
            value_dict["citizen_identifier"],
            now,
            site,
            value_dict["pc_name"],
            quarantined_from,
            login_duration,
            quarantine_duration,
            is_sms_booking,
        )
        # The citizen is allowed to log in or should be informed of
        # the time until next booking
        # (potentially that of someone else if idle login is allowed)
        # or the end of their quarantine
        if time_allowed:
            # Unless time_allowed < 0, the citizen is allowed to log in
            if time_allowed < 0:
                # Inform the citizen of the time until next booking
                # or the end of their quarantine
                citizen_hash = note
            elif (
                "allow_idle_login" in value_dict
            ):  # Idle logins are allowed, update Citizen object
                if citizen:  # Existing citizen
                    quarantined_from = citizen.last_successful_login + login_duration
                    if quarantined_from + quarantine_duration < now:
                        # If they are starting a new login period, update their
                        # last successful login
                        citizen.last_successful_login = now
                    citizen.logged_in = True
                else:  # First time login
                    citizen = Citizen(
                        citizen_id=citizen_hash,
                        last_successful_login=now,
                        site=site,
                        logged_in=True,
                    )
                citizen.save()

        else:  # Citizen is not allowed to log in
            citizen_hash = note
            # time_allowed will be None if idle login is not allowed
            # (or it is, but the citizen is quarantined or already logged in)
            # and no matching booking was found or if idle login is allowed,
            # but the computer is currently booked by someone else.
            # time_allowed will be 0 if the API validation failed
            if time_allowed is None and not note:
                if logged_in:
                    citizen_hash = "logged_in"
                else:
                    citizen_hash = "no_booking"
            return int(0), citizen_hash, log_id
    # If booking is not required, use the standard quarantine system.
    else:
        try:
            citizen = Citizen.objects.get(citizen_id=citizen_hash)
        except Citizen.DoesNotExist:
            citizen = None
        time_allowed = login_duration.total_seconds() // 60
        if citizen:
            quarantined_from = citizen.last_successful_login + login_duration
            if now < quarantined_from and not citizen.logged_in:
                time_allowed = (
                    time_allowed
                    - (now - citizen.last_successful_login).total_seconds() // 60
                )
                citizen.logged_in = True
            elif now < quarantined_from and citizen.logged_in:
                time_allowed = 0
                citizen_hash = "logged_in"
            elif (now - quarantined_from) >= quarantine_duration:
                citizen.last_successful_login = now
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

    # Only ever save a log if the citizen was actually allowed to log in
    if "save_log" in value_dict and time_allowed > 0:
        # Initially, logout_time = login_time
        login_log = LoginLog(
            identifier=value_dict["citizen_identifier"],
            site=site,
            date=datetime.date(now),
            login_time=datetime.time(now),
            logout_time=datetime.time(now),
        )
        login_log.save()
        log_id = login_log.id

    return int(time_allowed), citizen_hash, log_id


def general_citizen_logout(citizen_hash, log_id, client_key=None):
    """Update the logout time of the relevant LoginLog object if
    required and/or log out the relevant Citizen object if
    booking is not required."""

    # There is no reliable machine mapping on this endpoint today.
    _log_missing_machine_mapping_for_client_key("general_citizen_logout", client_key)

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


def sms_login(
    phone_number,
    message,
    pc_uid,
    require_booking=False,
    pc_name=None,
    allow_idle_login=False,
    login_duration=None,
    quarantine_duration=None,
    unlimited_access=False,
    client_key=None,
):
    """Check if the user is allowed to log in and if so, send a sms with
    the required password to the entered phone number.
    Whether a user is allowed to log in is determined by checking for a
    matching booking if booking is required or by checking the Citizen
    quarantine logic if booking is not required.
    If booking is required and idle logins are allowed, the Citizen
    quarantine logic will also be checked if the computer is not currently
    booked and the time until the next booking is greater than the
    login duration allowed by the Citizen quarantine logic.

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
        citizen_hash = 'sms_failed': Failed to authenticate with sms API.
        citizen_hash = 'quarantine' : Idle logins are allowed, but the
                       user is quarantined and does not have an active
                       booking or a future booking that starts before
                       the end of the quarantine.
        citizen_hash = 'booked' : Idle logins are allowed, but the
                       computer is currently booked by someone else.
        citizen_hash = 'later_booking' : The user cannot log in now,
                       but they have a booking that starts later.
        citizen_hash = 'booking_soon' : Idle logins are allowed, but
                       a future booking starts too soon for an idle
                       login to be possible."""
    citizen_hash = ""
    try:
        pc = PC.objects.get(uid=pc_uid)
        _enforce_client_key_for_pc("sms_login", pc, client_key)
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
        _log_missing_machine_mapping_for_client_key("sms_login", client_key)

    if login_duration:
        login_duration = timedelta(minutes=login_duration)
    else:
        login_duration = site.user_login_duration
    if quarantine_duration:
        quarantine_duration = timedelta(minutes=quarantine_duration)
    else:
        quarantine_duration = site.user_quarantine_duration

    now = datetime.now()
    # If booking is required then the bookings determine when and how long the
    # users can log in
    if require_booking:
        logged_in = False
        if allow_idle_login:
            citizen_hash = hashlib.sha512(str(phone_number[-8:]).encode()).hexdigest()
            try:
                citizen = Citizen.objects.get(citizen_id=citizen_hash)
            except Citizen.DoesNotExist:
                citizen = None
            if unlimited_access:
                # If the phone number has unlimited access
                # then we pretend that it is always their first login
                quarantined_from = False
            elif citizen:
                quarantined_from = citizen.last_successful_login + login_duration
                if (
                    citizen.logged_in
                    and not quarantined_from + quarantine_duration < now
                ):
                    # If the citizen is currently logged in on another computer,
                    # idle login should not be allowed
                    quarantined_from = None
                    logged_in = True
            else:
                # This is the citizen's first login seen by the quarantine system
                quarantined_from = False
        else:
            quarantined_from = None
        # Check for a matching booking
        time_allowed, note = easy_appointments_booking_validate(
            phone_number,
            now,
            site,
            pc_name,
            quarantined_from,
            login_duration,
            quarantine_duration,
        )
        # The citizen is allowed to log in or should be informed of
        # the time until next booking
        # (potentially that of someone else if idle login is allowed)
        if time_allowed:
            if time_allowed < 0:
                citizen_hash = note
        else:
            citizen_hash = note
            # time_allowed will be None if idle login is not allowed
            # (or it is, but the citizen is quarantined) and no matching
            # booking was found or if idle login is allowed, but
            # the computer is currently booked by someone else.
            # time_allowed will be 0 if the API validation failed
            if time_allowed is None and not note:
                if logged_in:
                    citizen_hash = "logged_in"
                else:
                    citizen_hash = "no_booking"
            return int(0), citizen_hash
    # If booking is not required and the phone number has
    # unlimited access, skip the quarantine system
    elif unlimited_access:
        time_allowed = login_duration.total_seconds() // 60
    # If booking is not required and the phone number does not have
    # unlimited access, use the standard quarantine system.
    # Don't update last_successful_login and logged_in until the
    # citizen actually logs in (sms_login_finalize)
    else:
        citizen_hash = hashlib.sha512(str(phone_number[-8:]).encode()).hexdigest()
        # Get previous login, if any.
        try:
            citizen = Citizen.objects.get(citizen_id=citizen_hash)
        except Citizen.DoesNotExist:
            citizen = None

        time_allowed = login_duration.total_seconds() // 60

        if citizen:
            quarantined_from = citizen.last_successful_login + login_duration
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


def sms_login_finalize(
    phone_number,
    pc_uid,
    require_booking,
    save_log,
    allow_idle_login=False,
    login_duration=None,
    quarantine_duration=None,
    client_key=None,
):
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
        _enforce_client_key_for_pc("sms_login_finalize", pc, client_key)
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
        _log_missing_machine_mapping_for_client_key("sms_login_finalize", client_key)
    # If booking is not required, we use the standard quarantine system
    # time_allowed has already been checked by sms_login, so we only need
    # to update last_successful_login and/or logged_in
    # The standard quarantine system is also used to keep track of idle logins
    if not require_booking or allow_idle_login:
        citizen_hash = hashlib.sha512(str(phone_number[-8:]).encode()).hexdigest()
        now = datetime.now()
        try:
            citizen = Citizen.objects.get(citizen_id=citizen_hash)
        except Citizen.DoesNotExist:
            citizen = None
        if login_duration:
            login_duration = timedelta(minutes=login_duration)
        else:
            login_duration = site.user_login_duration
        if quarantine_duration:
            quarantine_duration = timedelta(minutes=quarantine_duration)
        else:
            quarantine_duration = site.user_quarantine_duration
        if citizen:
            quarantined_from = citizen.last_successful_login + login_duration
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


def sms_logout(citizen_hash, log_id, client_key=None):
    """Update the logout time of the relevant LoginLog object if
    required and/or log out the relevant Citizen object if
    booking is not required."""

    val = general_citizen_logout(citizen_hash, log_id, client_key)
    return val


def citizen_login(
    username, password, pc_uid, prevent_dual_login=False, client_key=None
):
    """Check if user is allowed to log in and give the go-ahead if so.

    Return values:
        r < 0: User is quarantined and may login in -r minutes
        r = 0: Unable to authenticate.
        r > 0: The user is allowed r minutes of login time.
    """

    time_allowed = 0
    try:
        pc = PC.objects.get(uid=pc_uid)
        _enforce_client_key_for_pc("citizen_login", pc, client_key)
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
        _log_missing_machine_mapping_for_client_key("citizen_login", client_key)
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


def citizen_logout(citizen_hash, client_key=None):
    val = general_citizen_logout(citizen_hash, "", client_key)
    return val
