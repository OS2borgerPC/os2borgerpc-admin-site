from datetime import date
from dateutil.relativedelta import relativedelta
from ninja import Router
from typing import List
from ninja.pagination import paginate
from django.db.models import Q

from .models import APIKey, Configuration, ConfigurationEntry, Job, PC, SecurityEvent
from .api_schemas import (
    ConfigurationEntrySchema,
    JobSchema,
    PCSchema,
    SecurityEventSchema,
)

router = Router()

# TODO: Not sure what role "url_name" plays TBH
# The function name isn't important functionally, but it DOES determine what
# the endpoint is called in /api/docs (e.g. "list_users" becomes "List Users")


# TODO: Time filter jobs and security events


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


# TODO: Should we delete the individual endpoints and only have the lists?
# I think lists can make sense if we show less data per element on the list, and then use the individual endpoints to
# show more detailed information, but then they need somewhat different schema
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
    "/events",
    response=List[SecurityEventSchema],
    url_name="events",
    description="Fetch list of all events (e.g. Security Events), by default limited to the 100 most recent",
)
@paginate
def list_events(request):
    site = get_site_from_request(request)
    events = SecurityEvent.objects.filter(
        Q(problem__site=site) | Q(event_rule_server__site=site)
    ).order_by(
        "-id"
    )  # or -occurred_time
    if events:
        return events
    else:
        return []


# If no from_date: Default to three months ago, if no to_date, assume today.
@router.get(
    "/events/search",
    response=List[SecurityEventSchema],
    url_name="search-events",
    description="Fetch list of ....?, by default limited to the 100 most recent",
)
@paginate
def search_events(
    request,
    from_date=date.today() - relativedelta(months=3),
    to_date=date.today().isoformat(),
):
    site = get_site_from_request(request)
    # TODO: Maybe ensure dates aren't in the future, and aren't unreasonably far into the past?
    # Do we filter on do occurred_time, reported_time or created? Or multiple of them? Maybe occurred?
    events = SecurityEvent.objects.filter(
        (Q(problem__site=site) | Q(event_rule_server__site=site)),
        occurred_time__range=[from_date, to_date],
    ).order_by(
        "-id"
    )  # or -occurred_time
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
    event = SecurityEvent.objects.filter(
        Q(problem__site=site) | Q(event_rule_server__site=site), id=event_id
    ).first()
    if event:
        return 200, event
    else:
        return 204, None


# Configurations
@router.get(
    "/configuration/{int:configuration_id}",
    response={200: List[ConfigurationEntrySchema], 204: None},
    url_name="configuration",
    description="Fetch data on a specific PC Configuration, from a CONFIGURATION_ID which can be found via the pc endpoints. The configurations contain extended info about a PC, such as hostname, IP etc.",
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


# Jobs
@router.get(
    "/jobs",
    response={200: List[JobSchema], 204: None},
    url_name="jobs",
    description="Fetch a list of all Jobs, by default limited to the 100 most recent",
)
@paginate
def get_jobs(request):
    site = get_site_from_request(request)
    jobs = Job.objects.filter(batch__site=site)
    return (
        jobs or []
    )  # TODO: Test if this works. Otherwise do this: return jobs if jobs else []


@router.get(
    "/job/{int:job_id}",
    response={200: JobSchema, 204: None},
    url_name="job",
    description="Fetch data on a specific Job, from a JOB ID which can be found via Jobs endpoint. It is limited to the 100 most recent by default",
)
def get_job(request, job_id):
    site = get_site_from_request(request)
    job = Job.objects.filter(batch__site=site, id=job_id).first()
    if job:
        return 200, job
    else:
        return 204, None
