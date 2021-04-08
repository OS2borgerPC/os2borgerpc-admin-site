from django import template
register = template.Library()

# Don't think it's being used currently, so uncommenting for now
# @register.filter
# def sort_by(queryset, order):
#    return queryset.order_by(order)


# Add CSS classes to tags, e.g. django generated forms.
@register.filter
def add_class(field, class_name):
    return field.as_widget(attrs={
        "class": " ".join((field.css_classes(), class_name))
    })


@register.simple_tag
def css_class_current(current_url, match):
    if current_url.find(match) != -1:
        # Don't highlight Scripts when on security/scripts
        # Don't highlight Advarsler when on security/scripts
        if match == "scripts" and \
            current_url.find("security/scripts") != -1 or \
            match == "/security/" and \
            current_url.find("security/scripts") != -1:
                return
        return "active"
