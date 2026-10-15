import re

from django import forms

from .models import ContactMessage

PHONE_ALLOWED = re.compile(r'^\+?[\d\s().-]+$')
MESSAGE_MAX_LENGTH = 3000


class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    source = forms.CharField(required=False, widget=forms.HiddenInput)
    phone = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg bg-light border-0',
            'placeholder': '+233 20 000 0000', 'autocomplete': 'tel', 'inputmode': 'tel',
        }),
    )
    message = forms.CharField(
        max_length=MESSAGE_MAX_LENGTH,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-lg bg-light border-0', 'rows': 5,
            'placeholder': 'Tell us what you are looking for',
        }),
    )
    consent_to_contact = forms.BooleanField(
        required=True,
        label='I agree that EmanHomes may contact me about this enquiry.',
        error_messages={'required': 'Please confirm we may contact you about this enquiry.'},
    )

    class Meta:
        model = ContactMessage
        fields = (
            'name', 'email', 'phone', 'subject', 'message', 'inquiry_type',
            'preferred_contact', 'consent_to_contact',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-lg bg-light border-0', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-lg bg-light border-0', 'placeholder': 'you@example.com'}),
            'subject': forms.TextInput(attrs={'class': 'form-control form-control-lg bg-light border-0', 'placeholder': 'How can we help?'}),
            'inquiry_type': forms.Select(attrs={'class': 'form-select form-select-lg bg-light border-0'}),
            'preferred_contact': forms.Select(attrs={'class': 'form-select form-select-lg bg-light border-0'}),
            'consent_to_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = sum(ch.isdigit() for ch in phone)
        if not PHONE_ALLOWED.match(phone) or not 7 <= digits <= 15:
            raise forms.ValidationError('Enter a valid phone number, e.g. +233 20 584 3775.')
        return phone

    def clean_source(self):
        # Hidden field: trim rather than reject, so tampering cannot overflow the column.
        max_length = ContactMessage._meta.get_field('source').max_length
        return self.cleaned_data.get('source', '').strip()[:max_length]

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Unable to submit this form.')
        return ''
