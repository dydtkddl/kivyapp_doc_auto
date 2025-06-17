import os, re, shutil, logging
from datetime import datetime, date, timedelta, time

import fitz
from docx2pdf import convert
import pythoncom
from docxtpl import DocxTemplate
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction

from .forms import WorkForm
from .models import WorkFormDocument, WorkFormEntry

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\t\r\n]+','_',name).strip()


def create_context(data: dict) -> dict:
    def pd(d): return d.strftime('%y'),d.strftime('%m'),d.strftime('%d')
    yr,m1,d1 = pd(data['work_date']); yy,m2,d2 = pd(data['confirm_date'])
    st,et = data['start_time'], data['end_time']
    edate = date.today()+timedelta(1) if data['end_day']=='next' else date.today()
    dt_s = datetime.combine(date.today(), st)
    dt_e = datetime.combine(edate, et)
    if dt_e<dt_s: raise ValueError('종료시간 오류')
    mins = int((dt_e-dt_s).total_seconds()//60)
    hrs,mins = divmod(mins,60)
    return {
        'yr_01':yr,'mm_02':m1,'dd_03':d1,
        'location_04':data['location'],'device_05':data['device'],'carno_06':data['carno'],
        'hr_07':st.strftime('%H'),'min_08':st.strftime('%M'),
        'hr_09':et.strftime('%H'),'min_10':et.strftime('%M'),
        'hr_11':str(hrs),'min_12':f"{mins:02}",
        'work_content_13':data['work_content'],
        'yy_14':yy,'mm_15':m2,'dd_16':d2,
        'cert_17':data['cert_17'],'cert_18':data['cert_18'],
        'end_day':data['end_day']
    }

import pythoncom  # 파일 최상단에 추가

def form_view(request):
    docs = WorkFormDocument.objects.all()
    if request.method == 'POST':
        form = WorkForm(request.POST)
        if form.is_valid():
            raw = form.cleaned_data
            base = settings.BASE_STORAGE
            t = datetime.now().strftime('%Y%m%d_%H%M%S')
            slug = sanitize_filename(raw['location'])
            fld = f"{t}_{slug}"
            save_dir = os.path.join(base, fld)
            os.makedirs(save_dir, exist_ok=True)

            date_str = raw['work_date'].strftime('%Y%m%d')
            docx = f"{date_str}_{slug}_작업확인서.docx"
            img  = f"{date_str}_{slug}_preview.png"
            p_docx = os.path.join(save_dir, docx)
            p_img  = os.path.join(save_dir, img)

            try:
                # 1) DOCX 생성
                tpl = DocxTemplate(settings.BASE_DIR/'templates'/'작업확인서.docx')
                tpl.render(create_context(raw))
                tpl.save(p_docx)

                # 2) PDF 변환 (COM 초기화/해제)
                tmp_pdf = p_docx.replace('.docx', '_tmp.pdf')
                pythoncom.CoInitialize()
                try:
                    convert(p_docx, tmp_pdf)
                finally:
                    pythoncom.CoUninitialize()

                # 3) 이미지 추출
                pdf = fitz.open(tmp_pdf)
                pix = pdf[0].get_pixmap(dpi=150)
                pix.save(p_img)
                pdf.close()
                os.remove(tmp_pdf)

                # 4) DB 저장
                with transaction.atomic():
                    rel = os.path.relpath(save_dir, settings.MEDIA_ROOT)
                    doc = WorkFormDocument.objects.create(
                        folder_name=fld,
                        docx_file=os.path.join(rel, docx),
                        preview_image=os.path.join(rel, img)
                    )
                    WorkFormEntry.objects.create(
                        document=doc,
                        work_date=raw['work_date'], location=raw['location'],
                        device=raw['device'], carno=raw['carno'],
                        start_time=raw['start_time'], end_time=raw['end_time'],
                        end_day=raw['end_day'], work_content=raw['work_content'],
                        confirm_date=raw['confirm_date'], cert_17=raw['cert_17'], cert_18=raw['cert_18']
                    )

                messages.success(request, '저장 완료')
                return redirect('app:form')

            except Exception as e:
                logger.error(e)
                messages.error(request, f"오류: {e}")
        else:
            messages.error(request, '유효하지 않은 입력')
    else:
        form = WorkForm(initial={
            'work_date':    date.today(),
            'confirm_date': date.today(),
            'start_time':   time(9,0),
            'end_time':     time(18,0),
            'end_day':      'same',
        })

    return render(request, 'form.html', {'form': form, 'docs': docs})


def detail_view(request,pk):
    docs=WorkFormDocument.objects.all()
    doc=get_object_or_404(WorkFormDocument,pk=pk)
    entries=doc.entries.all()
    
    return render(request,'page.html',{'docs':docs,'doc':doc,'entries':entries})


def delete_view(request,pk):
    doc=get_object_or_404(WorkFormDocument,pk=pk)
    if request.method=='POST':
        # remove files
        dirpath=os.path.join(settings.BASE_STORAGE,doc.folder_name)
        if os.path.isdir(dirpath): shutil.rmtree(dirpath)
        doc.delete()
        messages.success(request,'삭제 완료')
        return redirect('app:form')
    return redirect('app:detail',pk=pk)


def edit_view(request, pk):
    docs = WorkFormDocument.objects.all()
    doc = get_object_or_404(WorkFormDocument, pk=pk)
    entry = doc.entries.first()

    if request.method == 'POST':
        form = WorkForm(request.POST)
        if form.is_valid():
            raw = form.cleaned_data

            # 1) 기존 폴더 삭제
            old_dir = os.path.join(settings.BASE_STORAGE, 'generated', doc.folder_name)
            if os.path.isdir(old_dir):
                shutil.rmtree(old_dir)

            # 2) 새 폴더명·경로 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            slug = sanitize_filename(raw['location'])
            new_folder = f"{timestamp}_{slug}"
            save_dir = os.path.join(settings.BASE_STORAGE, 'generated', new_folder)
            os.makedirs(save_dir, exist_ok=True)

            # 3) 파일명 정의
            date_str = raw['work_date'].strftime('%Y%m%d')
            docx_name = f"{date_str}_{slug}_작업확인서.docx"
            img_name  = f"{date_str}_{slug}_preview.png"
            docx_path = os.path.join(save_dir, docx_name)
            img_path  = os.path.join(save_dir, img_name)

            try:
                # 4) DOCX 생성
                tpl = DocxTemplate(settings.BASE_DIR / 'templates' / '작업확인서.docx')
                tpl.render(create_context(raw))
                tpl.save(docx_path)

                # 5) 이미지 변환
                tmp_pdf = docx_path.replace('.docx', '_tmp.pdf')
                # COM 초기화 후 변환, 완료 후 해제
                pythoncom.CoInitialize()
                try:
                    convert(docx_path, tmp_pdf)
                finally:
                    pythoncom.CoUninitialize()
                pdf = fitz.open(tmp_pdf)
                pix = pdf[0].get_pixmap(dpi=150)
                pix.save(img_path)
                pdf.close()
                os.remove(tmp_pdf)

                # 6) DB 업데이트
                with transaction.atomic():
                    rel_dir = os.path.relpath(save_dir, settings.MEDIA_ROOT)
                    # 문서 메타데이터 갱신
                    doc.folder_name = new_folder
                    doc.docx_file.name = os.path.join(rel_dir, docx_name)
                    doc.preview_image.name = os.path.join(rel_dir, img_name)
                    doc.save()

                    # 폼 입력 데이터 갱신
                    entry.work_date    = raw['work_date']
                    entry.location     = raw['location']
                    entry.device       = raw['device']
                    entry.carno        = raw['carno']
                    entry.start_time   = raw['start_time']
                    entry.end_time     = raw['end_time']
                    entry.end_day      = raw['end_day']
                    entry.work_content = raw['work_content']
                    entry.confirm_date = raw['confirm_date']
                    entry.cert_17      = raw['cert_17']
                    entry.cert_18      = raw['cert_18']
                    entry.save()

                messages.success(request, '문서 및 데이터가 성공적으로 수정되었습니다.')
                return redirect('app:detail', pk=doc.pk)

            except Exception as e:
                logger.error(f"Edit error: {e}")
                messages.error(request, f"오류 발생: {e}")

        else:
            messages.error(request, '유효하지 않은 입력입니다.')

    else:
        # GET: 기존 값을 초기값으로 form 생성
        form = WorkForm(initial={
            'work_date':    entry.work_date,
            'location':     entry.location,
            'device':       entry.device,
            'carno':        entry.carno,
            'start_time':   entry.start_time,
            'end_time':     entry.end_time,
            'end_day':      entry.end_day,
            'work_content': entry.work_content,
            'confirm_date': entry.confirm_date,
            'cert_17':      entry.cert_17,
            'cert_18':      entry.cert_18,
        })

    return render(request, 'edit.html', {
        'form': form,
        'docs': docs,
        'doc': doc,
    })