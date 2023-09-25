from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from typing import List
from django.db.models import Q

from ninja import Router
from ninja.pagination import paginate
from ninja.errors import ValidationError


from .models import (
    APIKey,
    Configuration,
    ConfigurationEntry,
    EventLevels,
    Job,
    PC,
    SecurityEvent,
)
from .api_schemas import (
    ConfigurationEntrySchema,
    Error,
    JobSchema,
    PCSchema,
    PCLoginsSchema,
    SecurityEventSchema,
)

router = Router()

# General notes:

# Endpoints use the names of the model on the english adminsite, whereas function names use the names of the models.
# TODO: EXCEPT SecurityEvents/Events currently, which we've forgotten to rename to Events in the models.
# API URLs use dashes as word separators

# We've wanted to combine @pagination with sending status codes in responses, but when used together it didn't work.
# In those cases we've instead used an empty list, instead of sending a specific HTTP response for "No content"

# TODO: Not sure what role "url_name" plays TBH
# The function name isn't important functionally, but it DOES determine what
# the endpoint is called in /api/docs (e.g. "list_users" becomes "List Users")


def get_site_from_request(request):
    """Obtains the site based on the API Key, from the request headers"""
    key = request.headers["Authorization"].split(" ")[-1]
    valid_key_check = APIKey.objects.filter(key=key).first()

    if valid_key_check:
        return valid_key_check.site


def validate_sensible_dates(from_date, to_date):
    if from_date > to_date:
        raise ValidationError("from_date is after to_date")
    elif to_date > date.today():
        raise ValidationError("to_date is in the future")


def filter_logins(all_logins, from_date, to_date):
    # Turn the string into a python list of tuples with any spaces removed
    # In other words it'll look like this:
    # [('2023-10-10', '4'), ('2023-10-11', '4'), ('2023-10-12', '3'), ('2023-10-16', '0')]
    all_logins_parsed = [
        tuple(x.replace(" ", "").split(":")) for x in all_logins.split(",")
    ]

    # Further turn the above into the format [(date, string)]
    all_logins_parsed = [
        (datetime.strptime(login[0], "%Y-%m-%d").date(), login[1])
        for login in all_logins_parsed
    ]
    return ", ".join(
        f"{date}: {logins}"
        for date, logins in all_logins_parsed
        if from_date <= date <= to_date
    )


# Computers
@router.get(
    "/computers",
    response=List[PCSchema],
    url_name="computers",
    description="Fetch list of all Computers.",
)
def list_pcs(request):
    site = get_site_from_request(request)
    pcs = PC.objects.filter(site=site)

    return pcs or []


# Events
# If no from_date: Default to three months ago, if no to_date, assume today.
# TODO: Write descriptions to the user about valid event levels and statuses
@router.get(
    "/events",
    response=List[SecurityEventSchema],
    url_name="events",
)
@paginate
def list_events(
    request,
    from_date: date = date.today() - relativedelta(months=3),
    to_date: date = date.today(),
    status=SecurityEvent.NEW,
):
    """
    Fetches events (Security Events and Offline Events).
    By default this endpoints returns jobs with:
     - **status**: New
       - Other options available, which you can pass along in the request to get different results:
       - Status: New, Assigned, Resolved
    """
    validate_sensible_dates(from_date, to_date)
    site = get_site_from_request(request)
    # Do we filter on do occurred_time, reported_time or created? Or multiple of them? Maybe occurred?
    events = SecurityEvent.objects.filter(
        (Q(problem__site=site) | Q(event_rule_server__site=site)),
        occurred_time__range=[from_date, to_date],
        status=status,
    ).order_by(
        "-id"
    )  # or -occurred_time, but ID is probably faster
    return events


# Configurations
@router.get(
    "/configuration/{int:configuration_id}",
    response={200: List[ConfigurationEntrySchema], 204: None},
    url_name="configuration",
    description="Fetch data on a specific Computer Configuration, from a CONFIGURATION_ID which can be found via the Computer endpoints. The configurations contain extended info about a PC, such as hostname, IP etc.",
)
def get_pc_configuration(request, configuration_id):
    site = get_site_from_request(request)
    config = Configuration.objects.filter(id=configuration_id).first()
    if config:
        pc = config.pc_set.first()
    if config and pc and pc.site == site:
        conf = ConfigurationEntry.objects.filter(owner_configuration=configuration_id)
        return 200, conf
    else:
        return 204, None


# Logins per day for all PCs (part of the Configuration)
# logins per day: send them in this format?: [('2023-01-02', 7), ('2023-01-01', 3)]  ...ie. a list of tuples with the
# name and the number of logins, from the latest to the earliest?
# if we don't have the number for a given day, set it to -1, None or something?
@router.get(
    "/computers/logins-per-day",
    response={200: List[PCLoginsSchema], 204: None},
    url_name="computers-logins-per-day",
    description="Fetch data on logins per day for all computers.",
)
def get_pcs_logins_per_day(
    request,
    from_date: date = date(1970, 1, 1),
    to_date: date = date.today(),
):
    site = get_site_from_request(request)
    pcs = PC.objects.filter(site=site, is_activated=True)
    pc_names_with_logins = []
    for pc in pcs:
        logins = pc.get_config_value("login_counts")
        # both set or either set: filter, neither set: don't filter
        if from_date != date(1970, 1, 1) or to_date != date.today():
            validate_sensible_dates(from_date, to_date)
            if logins:
                logins = filter_logins(logins, from_date, to_date)
        if logins:
            pc_names_with_logins.append({"pc_name": pc.name, "logins_per_day": logins})

    if pc_names_with_logins:
        print(type(pc_names_with_logins[0]))  # TODO: Debugging
        return 200, pc_names_with_logins
    else:
        return 204, None


# Logins per day for a single PC
@router.get(
    "/computers/{int:pc_id}/logins-per-day",
    response={200: PCLoginsSchema, 204: None},
    url_name="computer-logins-per-day",
    description="Fetch data on logins per day for a specific Computer, by its ID.",
)
def get_pc_logins_per_day(
    request,
    pc_id,
    from_date: date = date(1970, 1, 1),
    to_date: date = date.today(),
):
    site = get_site_from_request(request)
    try:
        pc = PC.objects.get(site=site, id=pc_id)
        logins = pc.get_config_value("login_counts")
    except PC.DoesNotExist:
        pc = None
    if pc and logins:
        # both set or either set: filter, neither set: don't filter
        if from_date != date(1970, 1, 1) or to_date != date.today():
            validate_sensible_dates(from_date, to_date)
            logins = filter_logins(logins, from_date, to_date)

        print(type({"pc_name": pc.name, "logins_per_day": logins}))
        return 200, {"pc_name": pc.name, "logins_per_day": logins}
    elif pc:
        return 200, {"pc_name": pc.name, "logins_per_day": ""}
    else:
        return 204, None
        # OR:
        # return 204, (None, None)


# Jobs
@router.get(
    "/jobs",
    response=List[JobSchema],
    url_name="jobs",
    description="Fetch a list of all Jobs.",
)
@paginate
def get_jobs(
    request,
    from_date: date = date.today() - relativedelta(months=3),
    to_date: date = date.today(),
):
    validate_sensible_dates(from_date, to_date)
    site = get_site_from_request(request)
    jobs = Job.objects.filter(
        batch__site=site, created__range=[from_date, to_date]
    ).order_by(
        "-id"
    )  # or -created, but ID is probably faster

    # TODO: Test if this works. Otherwise do this: return jobs if jobs else []
    return jobs or []


# Individual endpoints moved down here for now, as they may not be needed:

# TODO: Should we delete the individual endpoints and only have the lists?
# I think individual elements can make sense if we show less data per element on the list, and then use the individual endpoints to
# show more detailed information, but then they need somewhat different schema
# @router.get(
#    "/computers/{int:pc_id}",
#    response={200: PCSchema, 204: None},
#    url_name="computer",
#    description="Fetch data on a specific Computer, from the ID of a Computer.",
# )
# def get_pc(request, pc_id):
#    site = get_site_from_request(request)
#    pc = PC.objects.filter(site=site, id=pc_id).first()
#    if pc:
#        return 200, pc
#    else:
#        return 204, None


# @router.get(
#    "/jobs/{int:job_id}",
#    response={200: JobSchema, 204: None},
#    url_name="job",
#    description="Fetch data on a specific Job, from the ID of a Job.",
# )
# def get_job(request, job_id):
#    site = get_site_from_request(request)
#    job = Job.objects.filter(batch__site=site, id=job_id).first()
#    if job:
#        return 200, job
#    else:
#        return 204, None


# @router.get(
#    "/event/{int:event_id}",
#    response={200: SecurityEventSchema, 204: None},
#    url_name="event",
#    description="Fetch data on a specific event, from the ID of an event.",
# )
# def get_event(request, event_id):
#    site = get_site_from_request(request)
#    event = SecurityEvent.objects.filter(
#        Q(problem__site=site) | Q(event_rule_server__site=site), id=event_id
#    ).first()
#    if event:
#        return 200, event
#    else:
#        return 204, None
