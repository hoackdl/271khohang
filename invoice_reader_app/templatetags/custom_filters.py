from django import template

register = template.Library()

@register.filter
def hide_zero(value):
    try:
        if float(value) == 0:
            return ''
        return value
    except (ValueError, TypeError):
        return value
