from django import template
from django import forms
import math

register = template.Library()


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def is_password(field):
    return isinstance(field.field.widget, forms.PasswordInput)


@register.filter
def is_radioselect(field):
    return isinstance(field.field.widget, forms.RadioSelect)


@register.filter
def is_checkboxselectmultiple(field):
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)


@register.filter
def is_file(field):
    return isinstance(field.field.widget, forms.ClearableFileInput)

@register.filter
def can_unsubscribe(category, email_address):
    if category.cannot_unsubscribe and category.applies_to_email(email_address):
        return False

    return True

@register.filter
def normalize_mailing_score(score, r=150):
    # Find the circumference of the circle
    circumference = round(2*math.pi*r, 0)
    ratio = 10 / score
    normalized_value = circumference / ratio
    inverse_normal = circumference - normalized_value
    return math.ceil(inverse_normal)
