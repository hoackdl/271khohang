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


@register.filter
def split(value, sep=","):
    """Tách chuỗi thành list theo separator"""
    if not value:
        return []
    return value.split(sep)





@register.filter
def dict_get(d, key):
    return d.get(key, [])
