from django import forms

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    source = forms.CharField(required=False, widget=forms.HiddenInput)
    consent_to_contact = forms.BooleanField(
        required=True,
        label='I agree that EmanHomes may contact me about this enquiry.',
    )

    class Meta:
        model = ContactMessage
        fields = (
            'name', 'email', 'subject', 'message', 'inquiry_type',
            'preferred_contact', 'consent_to_contact',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-lg bg-light border-0', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-lg bg-light border-0', 'placeholder': 'you@example.com'}),
            'subject': forms.TextInput(attrs={'class': 'form-control form-control-lg bg-light border-0', 'placeholder': 'How can we help?'}),
            'message': forms.Textarea(attrs={'class': 'form-control form-control-lg bg-light border-0', 'rows': 5, 'placeholder': 'Tell us what you are looking for'}),
            'inquiry_type': forms.Select(attrs={'class': 'form-select form-select-lg bg-light border-0'}),
            'preferred_contact': forms.Select(attrs={'class': 'form-select form-select-lg bg-light border-0'}),
            'consent_to_contact': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_source(self):
        # Hidden field: trim rather than reject, so tampering cannot overflow the column.
        max_length = ContactMessage._meta.get_field('source').max_length
        return self.cleaned_data.get('source', '').strip()[:max_length]

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Unable to submit this form.')
        return ''
