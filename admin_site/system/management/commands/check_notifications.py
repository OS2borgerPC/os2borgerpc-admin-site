import logging
import traceback

from django.core.management.base import BaseCommand
from system.models import PC, EventRuleServer, SecurityEvent, User
from datetime import datetime
from django.core.mail import EmailMessage


class Command(BaseCommand):
    help = "Check if any notifications need to be sent"

    def handle(self, *args, **options):
        """Check if any pcs have been offline too long and send notifications"""

        all_pcs = PC.objects.only("last_seen").all().order_by("-pk")
        now = datetime.now()
        perform_check = False
        for pc in all_pcs:
            if pc.last_seen and (now - pc.last_seen).total_seconds() < 600:
                perform_check = True
                break

        if perform_check:
            logger = logging.getLogger(__name__)

            rules_to_check = EventRuleServer.objects.prefetch_related("alert_groups")
            for rule in rules_to_check:
                if rule.monitor_period_start < now.time() < rule.monitor_period_end:
                    email_dict = {}

                    if rule.alert_groups.first():
                        pcs_to_check_pk = list(
                            set(rule.alert_groups.values_list("pcs", flat=True))
                        )
                        pcs_to_check = PC.objects.only("name", "last_seen").filter(
                            pk__in=pcs_to_check_pk
                        )
                    else:
                        pcs_to_check = PC.objects.only("name", "last_seen").filter(
                            site=rule.site
                        )

                    for pc in pcs_to_check:
                        if (
                            pc.last_seen
                            and (now - pc.last_seen).total_seconds()
                            > rule.maximum_offline_period * 60
                        ):
                            try:
                                latest_event_time = (
                                    SecurityEvent.objects.only("reported_time")
                                    .filter(pc=pc, event_rule_server=rule)
                                    .order_by("-pk")
                                    .first()
                                    .reported_time
                                )
                                new_offline = pc.last_seen > latest_event_time
                            except AttributeError:
                                new_offline = True

                            if new_offline:
                                summary = (
                                    f"The Computer {pc.name} was offline for longer than "
                                    f"{rule.maximum_offline_period} minutes"
                                )
                                SecurityEvent.objects.create(
                                    event_rule_server=rule,
                                    pc=pc,
                                    occurred_time=now,
                                    reported_time=now,
                                    summary=summary,
                                )
                                supervisor_relations = pc.pc_groups.exclude(
                                    supervisors=None
                                )

                                if supervisor_relations:
                                    alert_users_pk = list(
                                        set(
                                            supervisor_relations.values_list(
                                                "supervisors", flat=True
                                            )
                                        )
                                    )
                                    alert_users = User.objects.only("email").filter(
                                        pk__in=alert_users_pk
                                    )
                                else:
                                    alert_users = rule.alert_users.only("email").all()

                                for user in alert_users:
                                    try:
                                        email_dict[user.email] += ", " + pc.name
                                    except KeyError:
                                        email_dict[user.email] = pc.name

                    for pcs in list(set(email_dict.values())):
                        email_list = []
                        for key, value in email_dict.items():
                            if pcs == value:
                                email_list.append(key)

                        body = "Notification:\n"
                        body += (
                            f"The computer(s) {pcs} have been offline for longer than "
                            f"{rule.maximum_offline_period} minutes"
                        )
                        try:
                            message = EmailMessage(
                                f"Notification rule: {rule.name}",
                                body,
                                to=email_list,
                            )
                            message.send(fail_silently=False)
                        except Exception:  # Likely Exception: SMTPException
                            logger.warning("Notification e-mail-sending failed:")
                            logger.warning(traceback.format_exc())
