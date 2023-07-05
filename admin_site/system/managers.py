from django.db import models


class SecurityEventQuerySet(models.QuerySet):
    def latest_event(self):
        """Get latest security event for pc."""
        return self.order_by("-reported_time").first()

    def priority_events_for_site(self, site):
        """Get priority events for a site."""
        from system.models import SecState, SecurityEvent

        return (
            self.filter(problem__site=site)
            .exclude(problem__level=SecState.NORMAL)
            .exclude(status=SecurityEvent.RESOLVED)
            .union(
                self.filter(event_rule_server__site=site)
                .exclude(event_rule_server__level=SecState.NORMAL)
                .exclude(status=SecurityEvent.RESOLVED)
            )
        )
