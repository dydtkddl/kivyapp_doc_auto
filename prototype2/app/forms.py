from django import forms
from .models import DAY_CHOICES

class WorkForm(forms.Form):
    work_date = forms.DateField(
        label='작업일자',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )
    location = forms.CharField(
        label='현장명',
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '예: 서울지점'
            }
        )
    )
    device = forms.CharField(
        label='장비명',
        max_length=100,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '예: 크레인'
            }
        )
    )
    carno = forms.CharField(
        label='차량번호',
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '예: 12가3456'
            }
        )
    )
    start_time = forms.TimeField(
        label='시작시간',
        widget=forms.TimeInput(
            attrs={'type': 'time', 'class': 'form-control'}
        )
    )
    end_time = forms.TimeField(
        label='종료시간',
        widget=forms.TimeInput(
            attrs={'type': 'time', 'class': 'form-control'}
        )
    )
    end_day = forms.ChoiceField(
        label='종료일',
        choices=DAY_CHOICES,
        widget=forms.Select(
            attrs={'class': 'form-select'}
        )
    )
    work_content = forms.CharField(
        label='작업내용',
        widget=forms.Textarea(
            attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': '구체적인 작업 내용을 입력해주세요'
            }
        )
    )
    confirm_date = forms.DateField(
        label='확인일자',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        )
    )
    cert_17 = forms.CharField(
        label='차단팀장명',
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )
    cert_18 = forms.CharField(
        label='현장책임자명',
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control'}
        )
    )