from django import forms

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Your Name',
            'id': 'name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Your Email',
            'id': 'email'
        })
    )
    subject = forms.CharField(
        max_length=200, 
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Subject',
            'id': 'subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'placeholder': 'Leave a message here',
            'id': 'message',
            'style': 'height: 150px'
        })
    )