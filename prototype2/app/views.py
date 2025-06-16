import os
import re
import logging
from datetime import datetime, date, timedelta, time

import fitz  # PyMuPDF
from docx2pdf import convert
from docxtpl import DocxTemplate
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from .forms import WorkForm
from .models import WorkFormDocument, WorkFormEntry

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\t\r\n]+', '_', name).strip()


def create_context(data: dict) -> dict:
    # 날짜 분해
    def parse_date(d):
        return d.strftime('%y'), d.strftime('%m'), d.strftime('%d')

    yr, m1, d1 = parse_date(data['work_date'])
    yy, m2, d2 = parse_date(data['confirm_date'])
    start = data['start_time']
    end = data['end_time']
    # 종료일 처리
    if data['end_day'] == 'next':
        end_date = date.today() + timedelta(days=1)
    else:
        end_date = date.today()
    dt_start = datetime.combine(date.today(), start)
    dt_end = datetime.combine(end_date, end)
    if dt_end < dt_start:
        # 날짜 선택 오류
        raise ValueError('종료일/시간이 시작일/시간보다 빠릅니다.')
    total_minutes = int((dt_end - dt_start).total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)

    return {
        'yr_01': yr,
        'mm_02': m1,
        'dd_03': d1,
        'location_04': data['location'],
        'device_05': data['device'],
        'carno_06': data['carno'],
        'hr_07': start.strftime('%H'),
        'min_08': start.strftime('%M'),
        'hr_09': end.strftime('%H'),
        'min_10': end.strftime('%M'),
        'hr_11': str(hours),
        'min_12': f"{minutes:02}",
        'work_content_13': data['work_content'],
        'yy_14': yy,
        'mm_15': m2,
        'dd_16': d2,
        'cert_17': data['cert_17'],
        'cert_18': data['cert_18'],
        # 필요시 템플릿에 삽입
        'end_day': data['end_day'],
    }


def form_view(request):
    docs = WorkFormDocument.objects.all()
    if request.method == 'POST':
        form = WorkForm(request.POST)
        if form.is_valid():
            raw = form.cleaned_data
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_loc = sanitize_filename(raw['location'])
            folder = f"{timestamp}_{safe_loc}"
            save_dir = os.path.join(settings.MEDIA_ROOT, 'generated', folder)
            os.makedirs(save_dir, exist_ok=True)

            docx_name = f"{folder}_작업확인서.docx"
            img_name = f"{folder}_preview.png"
            docx_path = os.path.join(save_dir, docx_name)
            img_path = os.path.join(save_dir, img_name)

            try:
                # DOCX 생성
                tpl_path = settings.BASE_DIR / 'templates' / '작업확인서.docx'
                tpl = DocxTemplate(tpl_path)
                tpl.render(create_context(raw))
                tpl.save(docx_path)

                # 이미지 변환
                tmp_pdf = docx_path.replace('.docx', '_tmp.pdf')
                convert(docx_path, tmp_pdf)
                pdf = fitz.open(tmp_pdf)
                pix = pdf[0].get_pixmap(dpi=150)
                pix.save(img_path)
                pdf.close()
                os.remove(tmp_pdf)

                # DB 저장
                with transaction.atomic():
                    rel = os.path.relpath(save_dir, settings.MEDIA_ROOT)
                    doc = WorkFormDocument.objects.create(
                        folder_name=folder,
                        docx_file=os.path.join(rel, docx_name),
                        preview_image=os.path.join(rel, img_name)
                    )
                    WorkFormEntry.objects.create(
                        document=doc,
                        work_date=raw['work_date'],
                        location=raw['location'],
                        device=raw['device'],
                        carno=raw['carno'],
                        start_time=raw['start_time'],
                        end_time=raw['end_time'],
                        end_day=raw['end_day'],
                        work_content=raw['work_content'],
                        confirm_date=raw['confirm_date'],
                        cert_17=raw['cert_17'],
                        cert_18=raw['cert_18']
                    )

                messages.success(request, '문서 및 데이터가 성공적으로 저장되었습니다.')
                return redirect('app:detail', pk=doc.pk)
            except Exception as e:
                logger.error(f"Document generation error: {e}")
                messages.error(request, f"오류 발생: {e}")
        else:
            messages.error(request, '유효하지 않은 입력입니다.')
    else:
        initial = {
            'work_date': date.today(),
            'confirm_date': date.today(),
            'start_time': time(9, 0),
            'end_time': time(18, 0),
            'end_day': 'same',
        }
        form = WorkForm(initial=initial)
    return render(request, 'form.html', {'form': form, 'docs': docs})


def detail_view(request, pk):
    doc = get_object_or_404(WorkFormDocument, pk=pk)
    entries = doc.entries.all()
    return render(request, 'page.html', {'doc': doc, 'entries': entries})