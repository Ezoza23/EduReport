from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key), None) or dictionary.get(key, None)
@register.filter
def index(lst, i):
    try:
        return lst[i]
    except (IndexError, TypeError):
        return ""