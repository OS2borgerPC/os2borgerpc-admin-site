"""Utility methods for the OS2borgerPC project."""

import json
import logging
import re
import requests
import traceback
from urllib.parse import quote

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


def easy_appointments_booking_validate(phone_number, date_time, site, pc_name=None):
    """Validate that the user has a booking for the current time
    and returns the end time of that booking if one is found.
    If a future booking is found, return the start time of that
    booking and an indication that it is a future booking.

    Return values:
        booking_time = None: No matching booking was found.
        booking_time = 0: Authentication with the API failed.
        booking_time = datetime string: The end time of an active
                        booking or the start time of a future booking.
        later_booking = False: No future booking.
        later_booking = True: The next matching booking is in the future."""

    logger = logging.getLogger(__name__)

    headers = {"Authorization": f"Bearer {site.booking_api_key}"}
    date = date_time.split(" ")[0]
    if not site.booking_api_url:
        logger.error(f"{site.name}: Booking API URL MUST be specified.")
        return 0, False
    appointment_url = (
        f"https://{site.booking_api_url}/index.php/api/v1/appointments?aggregates"
        f"&fields=start,end,customer,service&sort=+start&q={date}"
    )
    try:
        response = requests.get(appointment_url, headers=headers)
    # Likely Exceptions: socket.gaierror, NewConnectionError, MaxRetryError
    except Exception:
        return 0, False
    if response.ok:
        appointments = response.json()
    else:
        # Unable to authenticate with system API key - log this.
        message = response.text
        logger.error(
            f"{site.name} was unable to authorize with configured EasyAppointments API key: {message}"
        )
        return 0, False
    booking_time = None
    later_booking = False
    for appointment in appointments:
        if (
            (pc_name and appointment["service"]["name"].lower() == pc_name.lower())
            or not pc_name
        ) and appointment["customer"]["phone"][-8:] == phone_number[-8:]:
            if appointment["start"] < date_time < appointment["end"]:  # Current booking
                booking_time = appointment["end"]
                break
            elif date_time < appointment["start"]:  # Future booking
                later_booking = True
                booking_time = appointment["start"]
                break
    return booking_time, later_booking


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
    if not site.isil:
        logger.error(f"{site.name}: Agency ID / ISIL MUST be specified.")
        return 0
    # First, get sessionKey.
    session_key_url = (
        f"{settings.CICERO_URL}/rest/external/v1/{site.isil}/authentication/login/"
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
        f"{settings.CICERO_URL}/rest/external/{site.isil}/patrons/authenticate/v6"
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
    if not site.isil:
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
