from django.shortcuts import get_object_or_404
from ninja import Router
from typing import List
from ninja.pagination import paginate


from .models import APIKey, Configuration, ConfigurationEntry, PC, SecurityEvent, User
from .api_schemas import (
    ConfigurationEntrySchema,
    PCSchema,
    SecurityEventSchema,
)

router = Router()

# TODO: Not sure what role "url_name" plays TBH
# The function name isn't important functionally, but it DOES determine what
# the endpoint is called in /api/docs (e.g. "list_users" becomes "List Users")


def get_site_from_request(request):
    """Obtains the site based on the API Key, from the request headers"""
    key = request.headers["Authorization"].split(" ")[-1]
    valid_key_check = APIKey.objects.filter(key=key).first()

    if valid_key_check:
        return valid_key_check.site


# PCs
@router.get(
    "/pcs",
    response=List[PCSchema],
    url_name="pcs",
    description="Fetch list of all PCs, by default limited to 100",
)
@paginate
def list_pcs(request):
    site = get_site_from_request(request)
    pcs = PC.objects.filter(site=site)
    if pcs:
        return pcs
    else:
        return []


@router.get(
    "/pc/{int:pc_id}",
    response={200: PCSchema, 204: None},
    url_name="pc",
    description="Fetch data on a specific PC, from a PC_ID which can be found on the PC list",
)
def get_pc(request, pc_id):
    site = get_site_from_request(request)
    pc = PC.objects.filter(site=site, id=pc_id).first()
    if pc:
        return 200, pc
    else:
        return 204, None


# Events
@router.get(
    "/events/",
    response=List[SecurityEventSchema],
    url_name="events",
    description="Fetch list of all events (e.g. Security Events), by default limited to the 100 most recent",
)
@paginate
def list_events(request):
    site = get_site_from_request(request)
    events = SecurityEvent.objects.filter(problem__site=site).order_by("-id")  # or -occurred_time
    if events:
        return events
    else:
        return []


@router.get(
    "/event/{int:event_id}",
    response={200: SecurityEventSchema, 204: None},
    url_name="event",
    description="Fetch data on a specific event, from an EVENT_ID which can be found on the event list",
)
def get_event(request, event_id):
    site = get_site_from_request(request)
    event = SecurityEvent.objects.filter(problem__site=site, id=event_id).first()
    if event:
        return 200, event
    else:
        return 204, None


# Configurations
@router.get(
    "/configuration/{int:configuration_id}",
    response={200: List[ConfigurationEntrySchema], 204: None},
    url_name="configuration",
    description="Fetch data on a specific PC Configuration, from a CONFIGURATION_ID which can be found via the computer endpoints. This contains extended info about a PC, such as hostname, IP etc.",
)
def get_configuration(request, configuration_id):
    site = get_site_from_request(request)
    config = Configuration.objects.filter(id=configuration_id).first()
    if config:
        pc = config.pc_set.first()
    if config and pc.site == site:
        conf = ConfigurationEntry.objects.filter(owner_configuration=configuration_id)
        return 200, conf
    else:
        return 204, None
