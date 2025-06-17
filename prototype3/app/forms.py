# app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '이메일'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '아이디'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': '비밀번호'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': '비밀번호 확인'
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email

from django import forms
from .models import WorkFormDocument, WorkFormEntry

class DocumentForm(forms.ModelForm):
    class Meta:
        model = WorkFormDocument
        fields = ('folder_name','docx_file','preview_image')
        widgets = {
            'folder_name': forms.TextInput(attrs={
                'class':'form-control','placeholder':'폴더명'
            }),
            'docx_file': forms.ClearableFileInput(attrs={'class':'form-control'}),
            'preview_image': forms.ClearableFileInput(attrs={'class':'form-control'}),
        }

class EntryForm(forms.ModelForm):
    class Meta:
        model = WorkFormEntry
        fields = [
            'work_date', 'location', 'device', 'carno',
            'start_time', 'end_time', 'end_day',
            'work_content', 'confirm_date',
            'cert_17', 'cert_18'
        ]
        widgets = {
            'work_date': forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'location': forms.TextInput(attrs={'class':'form-control','placeholder':'현장명'}),
            'device': forms.TextInput(attrs={'class':'form-control','placeholder':'장비명'}),
            'carno': forms.TextInput(attrs={'class':'form-control','placeholder':'차량번호'}),
            'start_time': forms.TimeInput(attrs={'type':'time','class':'form-control'}),
            'end_time': forms.TimeInput(attrs={'type':'time','class':'form-control'}),
            'end_day': forms.Select(attrs={'class':'form-select'}),
            'work_content': forms.Textarea(attrs={
                'class':'form-control','rows':5,'placeholder':'작업 내용을 입력하세요'
            }),
            'confirm_date': forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'cert_17': forms.TextInput(attrs={'class':'form-control','placeholder':'차단팀장명'}),
            'cert_18': forms.TextInput(attrs={'class':'form-control','placeholder':'현장책임자명'}),
        }
