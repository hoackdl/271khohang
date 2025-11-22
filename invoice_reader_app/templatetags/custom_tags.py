from django import template
register = template.Library()

@register.filter
def in_list(value, arg):
    """
    Kiểm tra value có trong arg (chuỗi phân tách bằng dấu phẩy)
    """
    return value in arg.split(',')
