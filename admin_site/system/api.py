from django.shortcuts import get_object_or_404
from ninja import Router
from typing import List
from ninja.pagination import paginate


from .models import APIKey, Configuration, ConfigurationEntry, PC, SecurityEvent, User
from .api_schemas import (
    ConfigurationEntrySchema,
    PCSchema,
    SecurityEventSchema,
    UserSchema,
)

router = Router()

# TODO: Not sure what role "url_name" plays TBH
# The function name isn't important functionally, but it DOES determine what
# the endpoint is called in /api/docs (e.g. "list_users" becomes "List Users")


def get_site_from_request(request):
    """Obtains the site based on the API Key, from the request headers"""
    key = request.headers["Authorization"].split(" ")[-1]
    valid_key_check = APIKey.objects.get(key=key)

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
    print(site)
    return PC.objects.filter(site=site)


@router.get(
    "/pc/{int:pc_id}",
    response=PCSchema,
    url_name="pc",
    description="Fetch data on a specific PC",
)
def get_pc(request, pc_id):
    return PC.objects.filter(site=site, id=pc_id)


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
    return SecurityEvent.objects.filter(site=site).order_by("-id")  # or -occurred_time


@router.get(
    "/event/{int:event_id}",
    response=SecurityEventSchema,
    url_name="event",
    description="Fetch data on a specific event, from an <EVENT ID> which can be found on the event list",
)
def get_event(request, event_id):
    site = get_site_from_request(request)
    return SecurityEvent.objects.filter(site=site, id=event_id)


# Configurations
# TODO: Do we want a list of configurations as well? In that case it needs to find them by finding the site's
# configuration, but also go through all their groups and computers to find their related configurations. I'm thinking
# it would be a pretty expensive operation?
@router.get(
    "/configuration/{int:configuration_id}",
    response=List[ConfigurationEntrySchema],
    url_name="configuration",
    description="Fetch data on a specific PC Configuration, from a <CONFIGURATION ID> which can be found via the computer endpoints. This contains extended info about a PC, such as hostname, IP etc.",
)
def get_configuration(request, configuration_id):
    site = get_site_from_request(request)
    config = Configuration.objects.get(id=configuration_id, site=site)
    if config.pc_set.all() or config.group_set.all() or config.site_set.all():
        conf = ConfigurationEntry.objects.filter(owner_configuration=configuration_id)
        return conf
