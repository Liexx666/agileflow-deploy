from decimal import Decimal, ROUND_HALF_UP

from django import template

register = template.Library()


@register.filter
def hours_duration(value):
    """Display the existing decimal-hours total as hours and minutes."""
    total_minutes = int((Decimal(str(value or 0)) * 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes:02d}m"
