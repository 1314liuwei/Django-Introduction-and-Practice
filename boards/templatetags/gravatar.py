import hashlib
from urllib.parse import urlencode
from django import template
from django.conf import settings

register = template.Library()

@register.filter # 默认使用函数名作为过滤器名
def gravatar(user): # 自定义模板标签
    email = user.email.lower().encode('utf-8')
    default = 'mm'
    size = 256
    url = 'https://www.gravatar.com/avatar/{md5}?{params}'.format(
        md5=hashlib.md5(email).hexdigest(),
        params=urlencode({'d': default, 's': str(size)})
    )
    return url