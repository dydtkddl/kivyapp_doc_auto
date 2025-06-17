import os
import re
import shutil
import logging
from datetime import datetime, date, timedelta, time

import fitz
from docx2pdf import convert
import pythoncom
from docxtpl import DocxTemplate

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.utils import timezone

from .models import WorkFormDocument, WorkFormEntry
from .forms import DocumentForm, EntryForm, SignUpForm

logger = logging.getLogger(__name__)


#────────────────────────────────────────────
# Helper functions
#────────────────────────────────────────────
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\t\r\n]+', '_', name).strip()


def create_context(data: dict) -> dict:
    # 날짜/시간 포맷팅 및 지속시간 계산
    def pd(d):
        return d.strftime('%y'), d.strftime('%m'), d.strftime('%d')

    yr, m1, d1 = pd(data['work_date'])
    yy, m2, d2 = pd(data['confirm_date'])
    st, et = data['start_time'], data['end_time']
    edate = date.today() + timedelta(1) if data['end_day'] == 'next' else date.today()
    dt_s = datetime.combine(date.today(), st)
    dt_e = datetime.combine(edate, et)
    if dt_e < dt_s:
        raise ValueError('종료시간이 시작시간보다 이전입니다.')
    total_min = int((dt_e - dt_s).total_seconds() // 60)
    hrs, mins = divmod(total_min, 60)

    return {
        'yr_01': yr, 'mm_02': m1, 'dd_03': d1,
        'location_04': data['location'],
        'device_05': data['device'],
        'carno_06': data['carno'],
        'hr_07': st.strftime('%H'), 'min_08': st.strftime('%M'),
        'hr_09': et.strftime('%H'), 'min_10': et.strftime('%M'),
        'hr_11': str(hrs), 'min_12': f"{mins:02}",
        'work_content_13': data['work_content'],
        'yy_14': yy, 'mm_15': m2, 'dd_16': d2,
        'cert_17': data['cert_17'],
        'cert_18': data['cert_18'],
        'end_day': data['end_day']
    }


#────────────────────────────────────────────
# Authentication Views
#────────────────────────────────────────────
def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '회원가입이 완료되었습니다.')
            return redirect('document_list')
        messages.error(request, '입력 내용을 확인해주세요.')
    else:
        form = SignUpForm()
    return render(request, 'app/register.html', {'form': form})


def find_username(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            messages.info(request, f'회원님의 아이디는 "{user.username}" 입니다.')
        except User.DoesNotExist:
            messages.error(request, '해당 이메일로 가입된 사용자가 없습니다.')
    return render(request, 'app/find_username.html')


def find_password(request):
    return PasswordResetView.as_view(
        template_name='app/find_password.html',
        email_template_name='app/password_reset_email.html',
        success_url=reverse_lazy('login')
    )(request)


#────────────────────────────────────────────
# Document & Entry CRUD Views
#────────────────────────────────────────────
@login_required
def document_list(request):
    docs = WorkFormDocument.objects.order_by('-created_at')
    return render(request, 'app/document_list.html', {'documents': docs})


@login_required
def document_detail(request, pk):
    doc = get_object_or_404(WorkFormDocument, pk=pk)
    entries = doc.entries.all()
    return render(request, 'app/document_detail.html', {'doc': doc, 'entries': entries})


@login_required
def document_create(request):
    if request.method == 'POST':
        doc_form = DocumentForm(request.POST, request.FILES)
        entry_form = EntryForm(request.POST)
        if doc_form.is_valid() and entry_form.is_valid():
            # 1) 파일·이미지 메타 저장
            doc = doc_form.save(commit=False)
            if not doc.folder_name:
                doc.folder_name = f"user_{request.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
            doc.save()
            # 2) 폼 입력 데이터 저장
            entry = entry_form.save(commit=False)
            entry.document = doc
            entry.save()
            messages.success(request, '작업확인서가 생성되었습니다.')
            return redirect('document_detail', pk=doc.pk)
        messages.error(request, '입력 데이터를 확인해주세요.')
    else:
        doc_form = DocumentForm()
        entry_form = EntryForm()
    return render(request, 'app/form.html', {
        'doc_form': doc_form,
        'entry_form': entry_form,
        'mode': '생성'
    })


@login_required
def document_edit(request, pk):
    doc = get_object_or_404(WorkFormDocument, pk=pk)
    entry = doc.entries.first()
    if request.method == 'POST':
        doc_form = DocumentForm(request.POST, request.FILES, instance=doc)
        entry_form = EntryForm(request.POST, instance=entry)
        if doc_form.is_valid() and entry_form.is_valid():
            doc_form.save()
            entry_form.save()
            messages.success(request, '작업확인서가 업데이트되었습니다.')
            return redirect('document_detail', pk=pk)
        messages.error(request, '입력 데이터를 확인해주세요.')
    else:
        doc_form = DocumentForm(instance=doc)
        entry_form = EntryForm(instance=entry)
    return render(request, 'app/edit.html', {
        'doc_form': doc_form,
        'entry_form': entry_form,
        'mode': '수정'
    })
