from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def add_days(value, days):
    """Add days to a date"""
    try:
        if value and days:
            return value + timedelta(days=int(days))
        return value
    except (ValueError, TypeError):
        return value

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    try:
        return dictionary.get(key, 0)
    except (AttributeError, TypeError):
        return 0

@register.filter
def subtract_days(value, days):
    """Subtract days from a date"""
    try:
        if value and days:
            return value - timedelta(days=int(days))
        return value
    except (ValueError, TypeError):
        return value

@register.filter
def days_until(value):
    """Get days until a date"""
    try:
        if value:
            from django.utils import timezone
            delta = value - timezone.now().date()
            return delta.days
        return None
    except (ValueError, TypeError):
        return None