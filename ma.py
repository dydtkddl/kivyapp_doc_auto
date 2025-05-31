from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.font_definitions import theme_font_styles

from kivy.core.text import LabelBase
from kivy.utils import platform
from kivy.metrics import dp
from kivy.clock import Clock
from datetime import datetime
from docxtpl import DocxTemplate
import os
import sys

# ✅ 한글+이모지 폰트 등록 (Windows 기준)
malgun_path = os.path.abspath("Malgun_seguiemj.ttf")
malgun_path = os.path.abspath("Malgun.ttf")
LabelBase.register(name="malgun", fn_regular=malgun_path)

class DynamicMDTextField(MDTextField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = "malgun"
        if self.multiline:
            self.size_hint_y = None
            self.height = dp(120)
            self.bind(text=self.adjust_height)
    
    def set_objects_labels(self):
        super().set_objects_labels()
        if hasattr(self, "_helper_text_label") and self._helper_text_label:
            self._helper_text_label.font_name = "malgun"
        if hasattr(self, "_hint_text_label") and self._hint_text_label:
            self._hint_text_label.font_name = "malgun"
    
    def adjust_height(self, *args):
        if self.multiline:
            lines = max(1, len(self.text.split('\n')))
            new_height = max(dp(56), dp(24) * lines + dp(32))
            self.height = min(new_height, dp(200))

class DynamicMDCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 0  # 시작은 0으로
        self.bind(children=self.update_height)

    def update_height(self, *args):
        Clock.schedule_once(self._update_height, 0.05)

    def _update_height(self, dt):
        total_height = 0
        for child in self.children:
            if hasattr(child, 'height'):
                total_height += child.height
        self.height = total_height + dp(32)  # 패딩 여유 포함

class WorkFormApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        for style in ["H4", "H5", "Body1", "Subtitle1", "Button"]:
            self.theme_cls.font_styles[style] = ["malgun", 18, False, 0.15]
        self.screen = MDScreen()
        self.inputs = {}
        today = datetime.now().strftime("%Y-%m-%d")
        self.fields = [
            ("> 작업일자", "work_date", "single", today),
            ("> 현장명", "location_04", "single", ""),
            ("> 장비명", "device_05", "single", ""),
            ("> 차량번호", "carno_06", "single", ""),
            ("> 작업시작시간 (HH:MM)", "start_time", "single", "09:00"),
            ("> 작업종료시간 (HH:MM)", "end_time", "single", "18:00"),
            ("> 작업내용", "work_content_13", "multiline", ""),
            ("> 작업확인일자", "confirm_date", "single", today),
            ("> 차단팀장명", "cert_17", "single", ""),
            ("> 현장책임자명", "cert_18", "single", ""),
        ]
        return self.create_ui()

    def create_ui(self):
        main_layout = MDBoxLayout(orientation='vertical')
        header = MDTopAppBar(
            title="작업확인서 생성기",
            md_bg_color=self.theme_cls.primary_color,
            specific_text_color=[1, 1, 1, 1],
            left_action_items=[["menu", lambda x: None]],
            right_action_items=[["refresh", self.reset_form]],
        )
        self.toolbar = header  # 🔴 반드시 저장
        main_layout.add_widget(header)
        Clock.schedule_once(self.set_toolbar_font, 0.1)
        scroll = MDScrollView()
        content_layout = MDBoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(24)],
            spacing=dp(16),
            adaptive_height=True
        )
        title_label = MDLabel(
            text="> 작업 정보를 입력해주세요",
            font_style="H5",
            halign="center",
            theme_text_color="Primary",
            size_hint_y=None,
            height=dp(48),
            font_name="malgun"
        )
        content_layout.add_widget(title_label)
        self.create_input_fields(content_layout)
        btn_layout = MDBoxLayout(
            orientation='vertical',
            padding=dp(16),
            size_hint_y=None,
            height=dp(88)
        )
        btn = MDRaisedButton(
            text="> DOCX 파일 생성",
            on_release=self.generate_docx,
            font_name='malgun',
            size_hint=(1, None),
            height=dp(56),
            md_bg_color=self.theme_cls.primary_color,
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1],
            elevation=3
        )
        btn_layout.add_widget(btn)
        btn_card = DynamicMDCard(elevation=2)
        btn_card.add_widget(btn_layout)
        content_layout.add_widget(btn_card)
        scroll.add_widget(content_layout)
        main_layout.add_widget(scroll)
        return main_layout
    def set_toolbar_font(self, *args):
        try:
            self.toolbar.ids.label_title.font_name = "malgun"
        except Exception as e:
            print("⚠️ 툴바 폰트 적용 실패:", e)


    def create_input_fields(self, parent_layout):
        basic_card = self.create_field_card("> 기본 정보", self.fields[0:4])
        parent_layout.add_widget(basic_card)
        time_card = self.create_field_card("> 작업 시간", self.fields[4:6])
        parent_layout.add_widget(time_card)
        content_card = self.create_field_card("> 작업 내용", [self.fields[6]])
        parent_layout.add_widget(content_card)
        confirm_card = self.create_field_card("> 확인 정보", self.fields[7:10])
        parent_layout.add_widget(confirm_card)

    def create_field_card(self, card_title, fields):
        card_layout = MDBoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(12),
            adaptive_height=True  # ✅ 꼭 필요
        )

        title = MDLabel(
            text=card_title,
            font_style="Subtitle1",
            theme_text_color="Primary",
            size_hint_y=None,
            height=dp(32),
            bold=True,
            font_name="malgun"
        )
        card_layout.add_widget(title)
        for label, key, field_type, default_value in fields:
            tf = DynamicMDTextField(
                hint_text=label,
                text=default_value,
                mode='rectangle',
                font_name='malgun',
                size_hint_y=None,
                height=dp(56) if field_type == "single" else dp(120),
                multiline=(field_type == "multiline")
            )
            if "날짜" in label:
                tf.helper_text = "YYYY-MM-DD 형식으로 입력"
                tf.helper_text_mode = "persistent"
            elif "시간" in label:
                tf.helper_text = "HH:MM 형식으로 입력 (예: 09:30)"
                tf.helper_text_mode = "persistent"
            self.inputs[key] = tf
            card_layout.add_widget(tf)
        card = DynamicMDCard(elevation=2)
        card.add_widget(card_layout)
        return card

    def reset_form(self, instance):
        today = datetime.now().strftime("%Y-%m-%d")
        defaults = {
            'work_date': today,
            'confirm_date': today,
            'start_time': "09:00",
            'end_time': "18:00"
        }
        for key, tf in self.inputs.items():
            tf.text = defaults.get(key, "")

    def generate_docx(self, instance):
        try:
            raw = {k: v.text.strip() for k, v in self.inputs.items()}
            required_fields = ['work_date', 'location_04', 'device_05', 'start_time', 'end_time']
            for field in required_fields:
                if not raw[field]:
                    field_names = dict([(f[1], f[0]) for f in self.fields])
                    raise ValueError(f"필수 항목을 입력해주세요: {field_names.get(field, field)}")
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
            save_path = f"./작업확인서_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            doc.save(save_path)
            self.show_success_dialog(f"✅ 성공적으로 생성되었습니다!\n📁 저장 위치: {save_path}")
        except Exception as e:
            self.show_error_dialog(f"❌ 오류 발생: {str(e)}")

    def show_success_dialog(self, message):
        self.dialog = MDDialog(
            title="🎉 생성 완료",
            text=message,
            buttons=[
                MDRaisedButton(
                    text="확인",
                    font_name="malgun",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()

    def show_error_dialog(self, message):
        self.dialog = MDDialog(
            title="⚠️ 오류",
            text=message,
            buttons=[
                MDRaisedButton(
                    text="확인",
                    font_name="malgun",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()

if __name__ == "__main__":
    WorkFormApp().run()
