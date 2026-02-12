# invoice_reader_app/templatetags/number_to_text.py
from django import template

register = template.Library()

def number_to_vietnamese_text(value):
    # TODO: Viết hàm chuyển số thành chữ tiếng Việt
    # Đây là ví dụ đơn giản, bạn có thể thay bằng hàm đầy đủ hơn
    return "Số tiền bằng chữ"

register.filter('number_to_vietnamese_text', number_to_vietnamese_text)
