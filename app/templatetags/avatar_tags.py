# yourapp/templatetags/avatar_tags.py
# (create the templatetags/ folder with an empty __init__.py if it doesn't exist)

from django import template

register = template.Library()

AVATAR_COLORS = [
    '#ff5a2c',  # brand orange
    '#3b82f6',  # blue
    '#22c55e',  # green
    '#f59e0b',  # amber
    '#8b5cf6',  # violet
    '#ec4899',  # pink
    '#14b8a6',  # teal
    '#f97316',  # orange
]

@register.filter
def avatar_color(pk):
    """Return a deterministic background colour based on the user's pk."""
    return AVATAR_COLORS[int(pk) % len(AVATAR_COLORS)]