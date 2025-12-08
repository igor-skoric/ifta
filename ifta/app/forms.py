from django import forms
import datetime

# Kvartali
QUARTER_CHOICES = [
    ("Q1", "Q1 (Jan–Mar)"),
    ("Q2", "Q2 (Apr–Jun)"),
    ("Q3", "Q3 (Jul–Sep)"),
    ("Q4", "Q4 (Oct–Dec)"),
]

# Godine (trenutna + 2 prethodne)
current_year = datetime.date.today().year
YEAR_CHOICES = [(str(y), str(y)) for y in range(current_year, current_year - 2, -1)]


class CombinedUploadForm(forms.Form):
    single_file = forms.FileField(label="Upload IFTA Miles Excel file")
    # multiple_files = forms.FileField(
    #     label="Upload Fuel Excel files"
    # )
    quarter = forms.ChoiceField(choices=[("", "Choose Quarter")] + QUARTER_CHOICES, label="Quarter")
    year = forms.ChoiceField(choices=YEAR_CHOICES, label="Year")
