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
