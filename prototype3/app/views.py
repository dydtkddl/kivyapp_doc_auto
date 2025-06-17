import os
import re
import shutil
import logging
from datetime import datetime, date, timedelta, time

import fitz
# from docx2pdf import convert
# from docxtpl import DocxTemplate
import subprocess  # 추가
from docxtpl import DocxTemplate
import fitz  # PyMuPDF
# import pythoncom

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
# app/views.py
from django.contrib.auth import login
from django.contrib import messages

def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '회원가입이 완료되었습니다.')
            return redirect('document_list')
        else:
            # form.errors 안에 field별, non_field_errors가 모두 담겨 있습니다.
            messages.error(request, '회원가입에 실패했습니다. 아래 오류를 확인해주세요.')
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
from django.db.models import F
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def document_list(request):
    # 1) 로그인 유저 문서만
    qs = WorkFormDocument.objects.filter(user=request.user)

    # 2) 검색어 q: 현장명(Entry.location)에 대해 icontains 검색
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(entries__location__icontains=q)

    # 3) 정렬 sort 파라미터 처리
    sort = request.GET.get('sort')
    if sort == 'date_asc':
        qs = qs.order_by('entries__work_date')
    elif sort == 'date_desc':
        qs = qs.order_by('-entries__work_date')
    elif sort == 'name_asc':
        qs = qs.order_by('entries__location')
    elif sort == 'name_desc':
        qs = qs.order_by('-entries__location')
    else:
        # 기본: 최신순(생성일)
        qs = qs.order_by('-created_at')

    # 중복 제거 (entries 조인 시)
    documents = qs.distinct()

    return render(request, 'app/document_list.html', {
        'documents': documents,
        'q': q,
        'sort': sort,
    })

@login_required
def document_delete(request, pk):
    # 본인 것인지 체크
    doc = get_object_or_404(WorkFormDocument, pk=pk, user=request.user)
    user_folder = sanitize_filename(request.user.username)
            # --- 2) 기존 폴더(파일 전체) 삭제 ---
    old_dir = os.path.join(
        settings.MEDIA_ROOT,
        settings.BASE_STORAGE,
        user_folder,
        doc.folder_name
    )
    if os.path.isdir(old_dir):
        shutil.rmtree(old_dir)
    if request.method == 'POST':
        doc.delete()
        messages.success(request, '문서가 삭제되었습니다.')
        return redirect('document_list')

    # POST 가 아니면 상세로 돌려보내거나 에러 처리
    messages.error(request, '잘못된 요청입니다.')
    return redirect('document_detail', pk=pk)
@login_required
def document_detail(request, pk):
    # 본인 소유인지 체크하면서 가져오기
    doc   = get_object_or_404(WorkFormDocument, pk=pk, user=request.user)
    entry = doc.entries.first()
    return render(request, 'app/document_detail.html', {
        'doc':   doc,
        'entry': entry,
    })
import subprocess
import fitz
from docxtpl import DocxTemplate

def convert_docx_to_pdf(docx_path: str) -> str:
    """
    LibreOffice CLI로 DOCX → PDF 변환. 
    CWD를 docx_path가 있는 폴더로 지정해서 동일 위치에 PDF 생성.
    """
    save_dir, docx_name = os.path.split(docx_path)
    # CWD를 save_dir로, 변환 대상만 파일명으로
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf", docx_name],
        cwd=save_dir,
        check=True
    )
    return os.path.join(save_dir, docx_name.replace(".docx", ".pdf"))


def generate_preview_image(pdf_path: str, img_path: str, dpi: int = 150) -> None:
    """PDF의 첫 페이지를 읽어 DPI 해상도로 이미지(JPG/PNG) 저장."""
    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=dpi)
    pix.save(img_path)
    doc.close()


@login_required
def document_create(request):
    if request.method == "POST":
        form = EntryForm(request.POST)
        if form.is_valid():
            raw = form.cleaned_data

            # 디렉토리·파일명 준비
            timestamp   = timezone.now().strftime("%Y%m%d_%H%M%S")
            slug        = sanitize_filename(raw["location"])
            user_folder = sanitize_filename(request.user.username)
            folder_name = f"{timestamp}_{slug}"

            save_dir = os.path.join(
                settings.MEDIA_ROOT, settings.BASE_STORAGE, user_folder, folder_name
            )
            os.makedirs(save_dir, exist_ok=True)

            date_str  = raw["work_date"].strftime("%Y%m%d")
            docx_name = f"{date_str}_{slug}_작업확인서.docx"
            docx_path = os.path.join(save_dir, docx_name)
            img_name  = f"{date_str}_{slug}_preview.jpg"   # JPG로 변경
            img_path  = os.path.join(save_dir, img_name)

            try:
                # 1) DOCX 생성
                tpl = DocxTemplate(os.path.join(settings.BASE_DIR, "config/작업확인서.docx"))
                tpl.render(create_context(raw))
                tpl.save(docx_path)

                # 2) PDF 변환
                pdf_path = convert_docx_to_pdf(docx_path)

                # 3) 미리보기 이미지 생성
                generate_preview_image(pdf_path, img_path)

                # 4) 임시 PDF 삭제
                os.remove(pdf_path)

                # 5) DB 저장
                rel_dir = os.path.join(settings.BASE_STORAGE, user_folder, folder_name)
                with transaction.atomic():
                    doc = WorkFormDocument.objects.create(
                        user=request.user,
                        folder_name=folder_name,
                        docx_file=os.path.join(rel_dir, docx_name),
                        preview_image=os.path.join(rel_dir, img_name),
                    )
                    WorkFormEntry.objects.create(document=doc, **raw)

                messages.success(request, "작업확인서가 생성되었습니다.")
                return redirect("document_detail", pk=doc.pk)

            except subprocess.CalledProcessError as e:
                logger.error("PDF 변환 실패", exc_info=True)
                messages.error(request, "PDF 변환 중 오류가 발생했습니다.")
            except Exception as e:
                logger.error(e, exc_info=True)
                messages.error(request, f"문서 생성 중 오류가 발생했습니다: {e}")
        else:
            messages.error(request, "입력 내용을 확인해주세요.")
    else:
        form = EntryForm(initial={
            "work_date":    date.today(),
            "confirm_date": date.today(),
            "start_time":   time(9, 0),
            "end_time":     time(18, 0),
            "end_day":      "same",
        })

    return render(request, "app/form.html", {
        "entry_form": form,
        "mode":       "생성",
    })


@login_required
def document_edit(request, pk):
    doc   = get_object_or_404(WorkFormDocument, pk=pk, user=request.user)
    entry = doc.entries.first()

    if request.method == "POST":
        form = EntryForm(request.POST, instance=entry)
        if form.is_valid():
            raw = form.cleaned_data
            user_folder = sanitize_filename(request.user.username)

            # 기존 파일 제거
            old_dir = os.path.join(settings.MEDIA_ROOT, settings.BASE_STORAGE, user_folder, doc.folder_name)
            if os.path.isdir(old_dir):
                shutil.rmtree(old_dir)

            # 새 디렉토리·파일명 준비
            ts = timezone.now().strftime("%Y%m%d_%H%M%S")
            slug = sanitize_filename(raw["location"])
            folder_name = f"{ts}_{slug}"

            save_dir = os.path.join(settings.MEDIA_ROOT, settings.BASE_STORAGE, user_folder, folder_name)
            os.makedirs(save_dir, exist_ok=True)

            date_str  = raw["work_date"].strftime("%Y%m%d")
            docx_name = f"{date_str}_{slug}_작업확인서.docx"
            docx_path = os.path.join(save_dir, docx_name)
            img_name  = f"{date_str}_{slug}_preview.jpg"
            img_path  = os.path.join(save_dir, img_name)

            try:
                # 1) DOCX 생성
                tpl = DocxTemplate(os.path.join(settings.BASE_DIR, "config/작업확인서.docx"))
                tpl.render(create_context(raw))
                tpl.save(docx_path)

                # 2) PDF 변환
                pdf_path = convert_docx_to_pdf(docx_path)

                # 3) 이미지 생성
                generate_preview_image(pdf_path, img_path)

                # 4) 임시 PDF 삭제
                os.remove(pdf_path)

                # 5) DB 업데이트
                rel_dir = os.path.join(settings.BASE_STORAGE, user_folder, folder_name)
                with transaction.atomic():
                    doc.folder_name        = folder_name
                    doc.docx_file.name     = os.path.join(rel_dir, docx_name)
                    doc.preview_image.name = os.path.join(rel_dir, img_name)
                    doc.save()
                    form.save()

                messages.success(request, "작업확인서가 성공적으로 수정되었습니다.")
                return redirect("document_detail", pk=doc.pk)

            except subprocess.CalledProcessError:
                messages.error(request, "PDF 변환 중 오류가 발생했습니다.")
            except Exception as e:
                logger.error(e, exc_info=True)
                messages.error(request, f"수정 중 오류가 발생했습니다: {e}")
        else:
            messages.error(request, "입력 내용을 확인해주세요.")
    else:
        form = EntryForm(instance=entry)

    return render(request, "app/edit.html", {
        "form": form,
        "doc":  doc,
        "mode": "수정",
    })
