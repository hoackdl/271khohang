from django import template

register = template.Library()

@register.filter
def replace(value, old_new):
    parts = old_new.split(',', 1)
    if len(parts) != 2:
        return value
    old, new = parts
    return value.replace(old, new)



import json
from django import template

register = template.Library()

@register.filter
def jsonify(obj):
    """Chuyển object Python sang chuỗi JSON (dùng trong template)."""
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
