from django import template

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """Replace a field's value in the URL parameters"""
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()

@register.filter
def add_days(date, days):
    """Add days to a date"""
    from datetime import timedelta
    return date + timedelta(days=days)