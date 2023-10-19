from .models import ConfigurationEntry, Job, PC, SecurityEvent
from ninja import ModelSchema, Schema
from ninja.orm import create_schema

# Schemas are used by api.py, and it specifies things like which attributes are fetched for a given object

# UserSchema = create_schema(User, depth=1, fields=['username', 'groups'])
# PCSchema = create_schema(PC, depth=1, fields=['id', 'uid', "name", "pc_groups"])
# SecurityEventSchema = create_schema(SecurityEvent, depth=1, fields=['id', 'problem', "occurred_time", "reported_time",
#                                                                    "pc", "summary", "status", "assigned_user", "note"])

# Also fetches data about all its configuration entries
# ConfigurationSchema = create_schema(Configuration, depth=1, fields=['name'])


class Error(Schema):
    message: str


class PCSchema(ModelSchema):
    ip_addresses: str

    @staticmethod
    def resolve_ip_addresses(obj):
        return obj.get_config_value("_ip_addresses") or ""

    class Config:
        model = PC
        model_fields = [
            "id",
            "uid",
            "name",
            "location",
            "last_seen",
            "is_activated",
            "created",
            "pc_groups",
            "configuration",
        ]


# TODO: Should we fetch Security Problems as well? Maybe not, maybe just use depth1 so it shows up with its values as a foreign key instead of just an ID?
class SecurityEventSchema(ModelSchema):
    monitoring_rule: str
    level: str
    pc_name: str

    @staticmethod
    def resolve_monitoring_rule(obj):
        if obj.problem:
            return obj.problem.name
        else:
            return obj.event_rule_server.name

    @staticmethod
    def resolve_level(obj):
        if obj.problem:
            return obj.problem.level
        else:
            return obj.event_rule_server.level

    @staticmethod
    def resolve_pc_name(obj):
        return obj.pc.name

    class Config:
        model = SecurityEvent
        model_fields = [
            "id",
            "occurred_time",
            "pc",
            "summary",
            "status",
            "assigned_user",
            "note",
        ]


class ConfigurationEntrySchema(ModelSchema):
    class Config:
        model = ConfigurationEntry
        model_fields = ["key", "value"]


class JobSchema(ModelSchema):
    pc_name: str

    @staticmethod
    def resolve_pc_name(obj):
        return obj.pc.name

    class Config:
        model = Job
        model_fields = ["id", "status", "created", "started", "finished", "pc"]


class PCLoginsSchema(Schema):
    pc_name: str
    logins_per_day: str
