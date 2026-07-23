from django import template
register = template.Library()

# invoice_reader_app/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def in_list(value, arg):
    """Check if value is in comma-separated list"""
    return value in [x.strip() for x in arg.split(',')]


@register.filter
def abs(value):
    try:
        return abs(value)
    except:
        return value
