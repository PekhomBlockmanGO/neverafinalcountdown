import re
from django import forms
from .models import Ticket
from masters.models import Area, Location, SpecificArea


class QRComplaintForm(forms.ModelForm):
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        empty_label="Select building...",
        widget=forms.Select(attrs={'class': 'form-select custom-input'}),
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),     # ← show all; filter by qr_enabled only in QR flow
        empty_label="Select floor...",
        widget=forms.Select(attrs={'class': 'form-select custom-input'}),
    )
    specific_area = forms.ModelChoiceField(
        queryset=SpecificArea.objects.all(),
        empty_label="Select area...",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select custom-input'}),
    )

    class Meta:
        model = Ticket
        fields = [
            'area', 'location', 'specific_area',
            'category', 'description', 'reporter_phone', 'priority', 'photo',
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control custom-input',
                'rows': 3,
                'placeholder': 'Describe the problem...',
            }),
            'reporter_phone': forms.TextInput(attrs={
                'class': 'form-control custom-input',
                'placeholder': '10-digit mobile number',
                'maxlength': '10',
                'inputmode': 'numeric',
            }),
            'priority': forms.Select(attrs={'class': 'form-select custom-input'}),
            'category': forms.Select(attrs={'class': 'form-select custom-input'}),
            'photo': forms.FileInput(attrs={
                'class': 'd-none',
                'id': 'id_photo',
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        is_qr = kwargs.pop('is_qr', False)
        super().__init__(*args, **kwargs)

        if is_qr:
            # QR flow — restrict to QR-enabled locations and lock location fields
            self.fields['location'].queryset = Location.objects.filter(qr_enabled=True)
            for field_name in ('area', 'location', 'specific_area'):
                self.fields[field_name].disabled = True
                self.fields[field_name].widget.attrs['style'] = (
                    'background-color:#e2e8f0 !important;'
                    'cursor:not-allowed;color:#64748b;'
                )

    def clean_reporter_phone(self):
        phone = self.cleaned_data.get('reporter_phone', '').strip()
        if phone:
            if not re.fullmatch(r'\d{10}', phone):
                raise forms.ValidationError(
                    "Please enter a valid 10-digit mobile number."
                )
        return phone

    def clean(self):
        cleaned = super().clean()
        area = cleaned.get('area')
        location = cleaned.get('location')

        # Ensure the chosen location actually belongs to the chosen building
        if area and location and location.area != area:
            self.add_error(
                'location',
                "The selected floor does not belong to the selected building.",
            )
        return cleaned
