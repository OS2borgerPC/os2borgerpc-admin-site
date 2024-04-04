"""Utility methods for the OS2borgerPC project."""

import json
import logging
import re
import requests
import traceback
from urllib.parse import quote
from datetime import datetime

from importlib import import_module

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.utils import translation
from django.utils.translation import gettext_lazy as _


def notify_users(security_event, security_problem, pc):
    """Notify users about security event."""

    logger = logging.getLogger(__name__)

    # Subject = security name,
    # Body = description + technical summary
    email_list = []
    supervisor_relations = pc.pc_groups.exclude(supervisors=None)
    if supervisor_relations:
        alert_users_pk = list(
            set(supervisor_relations.values_list("supervisors", flat=True))
        )
        alert_users = User.objects.only("email").filter(pk__in=alert_users_pk)
    else:
        alert_users = security_problem.alert_users.only("email").all()
    for user in alert_users:
        email_list.append(user.email)

    body = f"Beskrivelse af sikkerhedsadvarsel: {security_problem.description}\n"
    body += f"Kort resume af data fra log filen : {security_event.summary}"
    try:
        message = EmailMessage(
            f"Sikkerhedsadvarsel for PC : {pc.name}."
            f" Sikkerhedsregel : {security_problem.name}",
            body,
            settings.DEFAULT_FROM_EMAIL,
            email_list,
        )
        message.send(fail_silently=False)
    except Exception:  # Likely Exception: SMTPException
        logger.warning("Security Event e-mail-sending failed:")
        logger.warning(traceback.format_exc())
        return False

    return True


def get_citizen_login_api_validator():
    """Get the function used to validate library user login.

    The validator must take three parameters - username, password and a site
    identity. It will return a unique ID of the authenticated user if
    successful, and something that evaluates to false if unsuccesful.
    """
    path, function = settings.CITIZEN_LOGIN_API_VALIDATOR.rsplit(".", 1)

    module = import_module(path)
    validator = getattr(module, function)

    return validator


def quria_login_validate(site, loaner_number, pincode):
    """Validate a user's credentials against Quria's API."""
    logger = logging.getLogger(__name__)

    if not site.agency_id:  # ISIL/NCIP must be specified
        logger.error(f"{site.name}: Agency ID / NCIP MUST be specified.")
        return 0

    headers = {
        "accept": "application/json",
        "X-Axiell-Api-Key": site.citizen_login_api_key,
    }
    loaner_auth_url = (
        f"https://axiell.io/api/quriaEU/patron-lookup/quria-release/integrations/"
        f"ncip/{site.agency_id}/small?sno={loaner_number}&pwd={pincode}"
    )

    response = requests.get(loaner_auth_url, headers=headers)

    if response.ok:
        status = response.json()["status"]
        return status
    else:
        # Unable to authenticate with system API key - log this.
        message = response.json()["message"]
        logger.error(
            f"{site.name} was unable to log in with configured API key: {message}"
        )
        return 0


def easy_appointments_booking_validate(
    identifier,
    now,
    site,
    pc_name,
    quarantined_from,
    login_duration,
    quarantine_duration,
    is_sms_booking=True,
):
    """Validate that the user either has a booking for the current time
    or is allowed to perform an idle login. In either case, return the
    allowed login time.
    If neither is the case, return information that can be used to
    inform the user why they are not allowed to log in.

    Return values:
        time_allowed = None: No matching booking was found and
                             idle login is not allowed/possible.
        time_allowed > 0: Citizen is allowed to log in for
                          time_allowed minutes.
        time_allowed = 0: Authentication with the API failed.
        time_allowed < 0: Citizen is not allowed to log in due to
                          circumstances indicated by note.
        note = "booking_soon": Another person's booking starts soon.
        note = "booked": The computer is currently booked by someone else.
        note = "later_booking": The Citizen has a booking that starts later.
        note = "quarantine": The Citizen is quarantined and does not have
                             a current booking."""

    logger = logging.getLogger(__name__)

    headers = {"Authorization": f"Bearer {site.booking_api_key}"}
    date_time = now.strftime("%Y-%m-%d %H:%M:%S")
    date = date_time.split(" ")[0]
    if not site.booking_api_url:
        logger.error(f"{site.name}: Booking API URL MUST be specified.")
        return 0, ""
    appointment_url = (
        f"https://{site.booking_api_url}/index.php/api/v1/appointments?aggregates"
        f"&fields=start,end,customer,service&sort=+start&q={date}"
    )
    try:
        response = requests.get(appointment_url, headers=headers)
    # Likely Exceptions: socket.gaierror, NewConnectionError, MaxRetryError
    except Exception:
        return 0, ""
    if response.ok:
        appointments = response.json()
    else:
        # Unable to authenticate with system API key - log this.
        message = response.text
        logger.error(
            f"{site.name} was unable to authorize with configured EasyAppointments API key: {message}"
        )
        return 0, ""
    time_allowed = None
    note = ""
    quarantine = False
    # If quarantined_from is None, idle login is not allowed.
    # Idle login only works with pc-specific booking.
    if quarantined_from is not None and pc_name:
        if (
            not quarantined_from or quarantined_from + quarantine_duration < now
        ):  # Citizen is starting a new login period
            idle_check = True
            now_plus_remaining_login_str = (now + login_duration).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        elif now < quarantined_from:  # Citizen is continuing the current login period
            idle_check = True
            now_plus_remaining_login_str = quarantined_from.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:  # If the citizen is quarantined, idle login is not possible.
            idle_check = False
            quarantine = True
    else:
        idle_check = False
    if is_sms_booking:
        # For SMS booking, we only use the last 8 characters of the identifier
        # (phone number) to check for a booking in order to prevent issues
        # related to the prepending of the country code
        chars = 8
    else:
        # For other types of booking, we use the full identifier
        # to check for a booking
        chars = 100
    for appointment in appointments:
        # Check whether idle login is possible
        if idle_check and appointment["service"]["name"].lower() == pc_name.lower():
            # Idle login is possible if the remaining login time is less than the
            # time until the start of the next booking
            if now_plus_remaining_login_str < appointment["start"]:
                # Idle login is possible. Duration is determined after the for loop.
                # If idle login is possible, we don't care if the user has a later booking.
                break
            time_to_next_booking = (
                datetime.strptime(appointment["start"], "%Y-%m-%d %H:%M:%S") - now
            )
            if (
                date_time < appointment["start"]
                and time_to_next_booking < login_duration
            ):
                # Idle login is not possible because the next booking is too close
                idle_check = False
                time_allowed = -(time_to_next_booking.total_seconds() // 60)
                note = "booking_soon"
            elif appointment["start"] < date_time < appointment["end"]:
                # Idle login is not possible because the computer is currently booked
                idle_check = False
                note = "booked"

        # Check for a matching booking
        if (
            (pc_name and appointment["service"]["name"].lower() == pc_name.lower())
            or not pc_name
        ) and appointment["customer"]["phone"][-chars:] == identifier[-chars:]:
            if appointment["start"] < date_time < appointment["end"]:  # Current booking
                # If the citizen has a current booking, they can always log in
                # regardless of quarantine status
                time_allowed = (
                    datetime.strptime(appointment["end"], "%Y-%m-%d %H:%M:%S") - now
                ).total_seconds() // 60
                note = ""
                break
            elif date_time < appointment["start"]:  # Future booking
                note = "later_booking"
                time_allowed = -(
                    (
                        datetime.strptime(appointment["start"], "%Y-%m-%d %H:%M:%S")
                        - now
                    ).total_seconds()
                    // 60
                )
                break
            elif note == "booked":
                # The computer is currently booked by someone else
                # No need for further checks
                break
    if idle_check:  # Idle login is allowed and possible
        if not quarantined_from or (quarantined_from + quarantine_duration) < now:
            # The user is starting a new login period
            time_allowed = login_duration
        else:  # The user is continuing the current login period
            time_allowed = quarantined_from - now
        time_allowed = time_allowed.total_seconds() // 60
    elif quarantine:  # The citizen is quarantined.
        remaining_quarantine = -(
            (quarantined_from + quarantine_duration - now).total_seconds() // 60
        )
        # If the citizen also has a later booking, but it starts after
        # their quarantine expires, inform them of their remaining quarantine
        # instead.
        if (
            note == "later_booking" and remaining_quarantine > time_allowed
        ) or time_allowed is None:
            time_allowed = remaining_quarantine
            note = "quarantine"
    return time_allowed, note


def send_password_sms(phone_number, message, site):
    """Makes a request to the SMSTeknik API in order to send
    a sms with the required password to the specified number.

    Return values:
        True: Request was successful.
        False: Authentication failed."""

    logger = logging.getLogger(__name__)

    sms_url = (
        f"https://api.smsteknik.se/send/xml/?id=F%F6reningen+Sambruk"
        f"&user={quote(site.citizen_login_api_user)}&pass={quote(site.citizen_login_api_password)}"
    )
    translate_table = str.maketrans({"å": r"&#229;", "ä": r"&#228;", "ö": r"&#246;"})
    xml = f"""<?xml version='1.0' encoding='utf-8'?>
        <sms-teknik>
        <flash>true</flash> # Make it a flash sms
        <customid>{site.name.translate(translate_table)}</customid>
        <udmessage><![CDATA[{message.translate(translate_table)}]]></udmessage>
        <smssender>MedborgarPC</smssender> # This is the listed sender. It is limited to 11 characters
        <items>
        <recipient>
        <nr>{phone_number}</nr>
        </recipient>
        </items>
        </sms-teknik>"""

    response = requests.post(sms_url, data=xml)
    # The SMSTeknik API always returns response.ok = True even
    # if authentication fails. Instead, status is indicated by
    # response.text which will be an id for successful requests
    # and 0: followed by a brief error description for failed
    # requests
    if response.text[:2] != "0:":
        return True
    else:
        # Unable to authenticate with system user - log this.
        logger.error(
            f"{site.name} was unable to authorize with SMSTeknik with configured user name and password"
        )
        return False


def cicero_validate(loaner_number, pincode, site):
    """Do the actual validation against the Cicero service.

    If successful, this function will return the Cicero Patron ID, otherwise it
    will return something falsey like None, 0 or ''.
    """
    logger = logging.getLogger(__name__)

    regex_match = re.fullmatch(f"^\d+$", pincode)
    if not regex_match:
        # logger.warning("{site.name}: Pincode must be a number.")
        return 0
    if not site.agency_id:
        logger.error(f"{site.name}: Agency ID / ISIL MUST be specified.")
        return 0
    # First, get sessionKey.
    session_key_url = (
        f"{settings.CICERO_URL}/rest/external/v1/{site.agency_id}/authentication/login/"
    )
    response = requests.post(
        session_key_url,
        json={
            "username": site.citizen_login_api_user,
            "password": site.citizen_login_api_password,
        },
    )
    if response.ok:
        session_key = response.json()["sessionKey"]
        # Just debugging for the moment.
    else:
        # Unable to authenticate with system user - log this.
        message = response.json()["message"]
        logger.error(
            f"{site.name} was unable to log in with configured user name and password: {message}"
        )
        return 0
    # We now have a valid session key.
    loaner_auth_url = (
        f"{settings.CICERO_URL}/rest/external/{site.agency_id}/patrons/authenticate/v6"
    )
    response = requests.post(
        loaner_auth_url,
        headers={"X-session": session_key},
        json={"libraryCardNumber": loaner_number, "pincode": pincode},
    )
    if response.ok:
        result = response.json()
        authenticate_status = result["authenticateStatus"]
        if authenticate_status != "VALID":
            # logger.warning(
            #    f"Unable to authenticate with loaner ID and pin: {authenticate_status}"
            # )
            return 0
        # Loaner has been successfully authenticated.
        patron_id = result["patron"]["patronId"]
        return patron_id


def always_validate_citizen(loaner_number, pincode, site):
    """Perform sanity checks, but always return a suitable patron ID."""
    logger = logging.getLogger(__name__)
    try:
        pincode = int(pincode)
    except ValueError:
        logger.warning(f"{site.name}: Pincode must be a number.")
        return 0
    if not site.agency_id:
        logger.error(f"{site.name}: Agency ID / ISIL MUST be specified.")
        return 0
    return loaner_number


def get_notification_string(python_list, conjunction="og"):
    """Helper function used to generate human-readable strings
    from python lists."""
    python_list = list(set(python_list))
    if len(python_list) > 1:
        string = ", ".join(python_list[:-1])
        string = " ".join([string, conjunction, python_list[-1]])
    elif len(python_list) == 1:
        string = python_list[0]
    else:
        string = ""
    return string


def set_notification_cookie(response, message, error=False):
    descriptor = {"message": message, "type": "success" if not error else "error"}

    response.set_cookie("page-notification", quote(json.dumps(descriptor), safe=""))


def notification_changes_saved(response, user_profile_language):
    translation.activate(user_profile_language)
    set_notification_cookie(response, _("Changes have been saved %s") % "")
    translation.deactivate()

    return response
