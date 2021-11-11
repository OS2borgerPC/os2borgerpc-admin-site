"""Utility methods for the OS2borgerPC project."""

import requests
import logging

from importlib import import_module

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage


def notify_users(data, security_problem, pc):
    """Notify users about security event."""

    # Subject = security name,
    # Body = description + technical summary
    email_list = []
    alert_users = security_problem.alert_users.all()
    for user in alert_users:
        email_list.append(User.objects.get(id=user.id).email)

    body = ("Beskrivelse af sikkerhedsadvarsel: " +
            security_problem.description + "\n")
    body += "Kort resume af data fra log filen : " + data[2]
    try:
        message = EmailMessage("Sikkerhedsadvarsel for PC : " + pc.name
                               + ". Sikkerhedsregel : " +
                               security_problem.name, body,
                               settings.DEFAULT_FROM_EMAIL, email_list)
        message.send(fail_silently=False)
    except Exception:
        return False

    return True


def get_citizen_login_validator():
    """Get the function used to validate library user login.

    The validator must take three parameters - username, password and a site
    identity. It will return a unique ID of the authenticated user if
    successful, and something that evaluates to false if unsuccesful.
    """
    path, function = settings.CITIZEN_LOGIN_VALIDATOR.rsplit('.', 1)

    module = import_module(path)
    validator = getattr(module, function)

    return validator


def cicero_validate(loaner_number, pincode, agency_id):
    """Do the actual validation against the Cicero service.

    If successful, this function will return the Cicero Patron ID, otherwise it
    will return something falsey like None, 0 or ''.
    """
    logger = logging.getLogger(__name__)
    try:
        pincode = int(pincode)
    except ValueError:
        logger.error(f"Pincode must be a number - {pincode} is not  number.")
        return 0
    if not agency_id:
        logger.error("Agency ID / ISIL MUST be specified.")
        return 0
    # First, get sessionKey.
    session_key_url = (
        f"{settings.CICERO_URL}/rest/external/v1/{agency_id}/authentication/login/"
    )
    response = requests.post(
        session_key_url,
        json={"username": settings.CICERO_USER, "password": settings.CICERO_PASSWORD},
    )
    if response.ok:
        session_key = response.json()["sessionKey"]
        # Just debugging for the moment.
    else:
        # TODO: Unable to authenticate with system user - log this.
        message = response.json()["message"]
        logger.error(
            f"Unable to log in with configured user name and password: {message}"
        )
        return 0
    # We now have a valid session key.
    loaner_auth_url = (
        f"{settings.CICERO_URL}/rest/external/{agency_id}/patrons/authenticate/v6"
    )
    response = requests.post(
        loaner_auth_url,
        headers={"X-session": session_key},
        json={"libraryCardNumber": loaner_number, "pincode": pincode},
    )
    if response.ok:
        result = response.json()
        authenticate_status = result["authenticateStatus"]
        print(authenticate_status)
        if authenticate_status != "VALID":
            logger.error(
                f"Unable to authenticate with loaner ID and pin: {authenticate_status}"
            )
            return 0
        # Loaner has been successfully authenticated.
        patron_id = result["patron"]["patronId"]
        return patron_id

    print(response)
