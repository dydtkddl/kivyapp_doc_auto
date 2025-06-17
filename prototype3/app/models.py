from django.db import models
import os
from django.conf import settings

# 종료일 선택지
DAY_CHOICES = [
    ('same', '당일'),
    ('next', '익일'),
]

def upload_to(instance, filename):
    """
    Save files under MEDIA_ROOT/<BASE_STORAGE>/<folder_name>/<filename>
    """
    base = getattr(settings, 'BASE_STORAGE', '')
    return os.path.join(base, instance.folder_name, filename)

class WorkFormDocument(models.Model):
    """
    Metadata for generated DOCX and preview image.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    folder_name = models.CharField('폴더명', max_length=255)
    docx_file = models.FileField('DOCX 파일', upload_to=upload_to)
    preview_image = models.ImageField('미리보기 이미지', upload_to=upload_to)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.folder_name

    @property
    def filename(self):
        return os.path.basename(self.docx_file.name)

class WorkFormEntry(models.Model):
    """
    User-entered form data for work confirmation.
    """
    document = models.ForeignKey(
        WorkFormDocument,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    work_date    = models.DateField('작업일자')
    location     = models.CharField('현장명', max_length=100)
    device       = models.CharField('장비명', max_length=100)
    carno        = models.CharField('차량번호', max_length=100, blank=True)
    start_time   = models.TimeField('시작시간')
    end_time     = models.TimeField('종료시간')
    end_day      = models.CharField('종료일', max_length=10, choices=DAY_CHOICES, default='same')
    work_content = models.TextField('작업내용')
    confirm_date = models.DateField('확인일자')
    cert_17      = models.CharField('차단팀장명', max_length=100, blank=True)
    cert_18      = models.CharField('현장책임자명', max_length=100, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Entry on {self.work_date} - {self.location}"