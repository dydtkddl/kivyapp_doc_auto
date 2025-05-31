import os
os.environ["KIVY_GL_BACKEND"] = "sdl2"

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog

from kivy.core.text import LabelBase
from kivy.utils import platform
from kivymd.font_definitions import theme_font_styles

from docxtpl import DocxTemplate
from datetime import datetime
import os

# 1. 한글 폰트 등록 (같은 폴더에 malgun.ttf 파일 필요)
font_path = os.path.abspath("malgun.ttf")
try:
    LabelBase.register(name='malgun', fn_regular=font_path)
except Exception as e:
    print("폰트 등록 실패:", e)

class WorkFormApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # 2. 기존 폰트 스타일 유지하면서 일부만 한글 폰트로 덮어쓰기
        self.theme_cls.font_styles["H5"] = ["malgun", 20, False, -1.5]
        self.theme_cls.font_styles["Body1"] = ["malgun", 16, False, 0.15]
        self.theme_cls.font_styles["Subtitle1"] = ["malgun", 14, False, 0.15]
        self.theme_cls.font_styles["Button"] = ["malgun", 14, True, 0.15]

        if "malgun" not in theme_font_styles:
            theme_font_styles.append("malgun")

        self.screen = MDScreen()
        self.inputs = {}

        self.fields = [
            ("작업일자 (YYYY-MM-DD)", "work_date"),
            ("현장명", "location_04"),
            ("장비명", "device_05"),
            ("차량번호", "carno_06"),
            ("작업시작시간 (HH:MM)", "start_time"),
            ("작업종료시간 (HH:MM)", "end_time"),
            ("작업내용", "work_content_13"),
            ("작업확인일자 (YYYY-MM-DD)", "confirm_date"),
            ("차단팀장명", "cert_17"),
            ("현장책임자명", "cert_18"),
        ]

        layout = MDBoxLayout(orientation='vertical', padding=10, spacing=10)
        for label, key in self.fields:
            tf = MDTextField(
                hint_text=label,
                mode='rectangle',
                font_name='malgun'
            )
            self.inputs[key] = tf
            layout.add_widget(tf)

        btn = MDRaisedButton(
            text="Generate DOCX",
            on_release=self.generate_docx,
            font_name='malgun'
        )
        layout.add_widget(btn)

        self.screen.add_widget(layout)
        return self.screen

    def generate_docx(self, instance):
        try:
            raw = {k: v.text.strip() for k, v in self.inputs.items()}

            def parse_date(date_str):
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt.strftime("%y"), dt.strftime("%m"), dt.strftime("%d")

            yr_01, mm_02, dd_03 = parse_date(raw["work_date"])
            yy_14, mm_15, dd_16 = parse_date(raw["confirm_date"])

            def parse_time(tstr):
                return datetime.strptime(tstr, "%H:%M")

            t_start = parse_time(raw["start_time"])
            t_end = parse_time(raw["end_time"])
            t_diff = t_end - t_start
            if t_diff.total_seconds() < 0:
                raise ValueError("작업 종료시간이 시작시간보다 빠릅니다.")
            total_minutes = int(t_diff.total_seconds() // 60)
            hr_11, min_12 = divmod(total_minutes, 60)

            hr_07, min_08 = t_start.strftime("%H"), t_start.strftime("%M")
            hr_09, min_10 = t_end.strftime("%H"), t_end.strftime("%M")

            context = {
                'yr_01': yr_01, 'mm_02': mm_02, 'dd_03': dd_03,
                'location_04': raw['location_04'],
                'device_05': raw['device_05'],
                'carno_06': raw['carno_06'],
                'hr_07': hr_07, 'min_08': min_08,
                'hr_09': hr_09, 'min_10': min_10,
                'hr_11': str(hr_11), 'min_12': f"{min_12:02}",
                'work_content_13': raw['work_content_13'],
                'yy_14': yy_14, 'mm_15': mm_15, 'dd_16': dd_16,
                'cert_17': raw['cert_17'], 'cert_18': raw['cert_18'],
            }

            doc = DocxTemplate("작업확인서.docx")
            doc.render(context)

            save_path = "./generated.docx"
            doc.save(save_path)

            MDDialog(title="성공", text=f"저장 완료: {save_path}").open()

        except Exception as e:
            MDDialog(title="오류 발생", text=str(e)).open()


if __name__ == "__main__":
    WorkFormApp().run()
