from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.navigationdrawer import MDNavigationDrawer, MDNavigationLayout
from kivymd.uix.list import OneLineAvatarIconListItem, ImageLeftWidget
from kivy.uix.screenmanager import ScreenManager
from kivy.core.text import LabelBase
from kivy.utils import platform
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.properties import ObjectProperty
from datetime import datetime
from docxtpl import DocxTemplate
import os
from kivy.uix.image import Image
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.metrics import dp

import tempfile
import re
import fitz            # PyMuPDF (pip install pymupdf)
from docx2pdf import convert  # DOCX → PDF 변환 (pip install docx2pdf)

def sanitize_filename(name):
    # 윈도우에서 불가한 문자와 제어문자를 _로 치환
    return re.sub(r'[\\/:*?"<>|\t\r\n]+', '_', name).strip()

# -------------------------------
# 상단에 저장 루트 폴더 경로 CONSTANT 정의
# -------------------------------
if platform == "android":
    from android.storage import app_storage_path
    SAVE_ROOT = app_storage_path()  # Android 앱 전용 저장 경로
else:
    SAVE_ROOT = os.path.abspath("generated_forms")  # PC/Windows 환경 시 기본 폴더

if not os.path.exists(SAVE_ROOT):
    os.makedirs(SAVE_ROOT, exist_ok=True)

# -------------------------------
# 한글 폰트 등록 (malgun.ttf 파일은 프로젝트 루트에 위치)
# -------------------------------
FONT_PATH = os.path.abspath("malgun.ttf")
LabelBase.register(name="malgun", fn_regular=FONT_PATH)

# -------------------------------
# DOCX → PDF → 이미지 변환 함수 (PyMuPDF + docx2pdf)
# -------------------------------
def convert_docx_to_image(docx_path, output_img_path):
    """
    1) docx2pdf.convert()로 임시 PDF 생성
    2) PyMuPDF(fitz)로 첫 페이지를 PNG로 저장
    """
    try:
        # 1) DOCX → PDF 변환
        tmp_pdf = docx_path.replace(".docx", "_temp.pdf")
        convert(docx_path, tmp_pdf)

        # 2) PDF → 이미지 (PyMuPDF)
        pdf_doc = fitz.open(tmp_pdf)
        page = pdf_doc[0]
        pix = page.get_pixmap(dpi=150)
        pix.save(output_img_path)
        pdf_doc.close()

        # 임시 PDF 파일 삭제
        os.remove(tmp_pdf)
        return True
    except Exception as e:
        print(f"이미지 변환 실패: {e}")
        return False

# -------------------------------
# 커스텀 위젯: 멀티라인일 때 자동 높이 조절 + 한글폰트 지정
# -------------------------------
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

# -------------------------------
# 커스텀 카드: 자식 위젯 높이에 맞춰 자동 높이 조절
# -------------------------------
class DynamicMDCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 0
        self.bind(children=self.update_height)

    def update_height(self, *args):
        Clock.schedule_once(self._update_height, 0.05)

    def _update_height(self, dt):
        total_height = sum(child.height for child in self.children if hasattr(child, "height"))
        self.height = total_height + dp(32)

# -------------------------------
# 메인 앱 클래스
# -------------------------------
class WorkFormApp(MDApp):
    nav_drawer = ObjectProperty()
    nav_list = ObjectProperty()

    def build(self):
        # 테마 설정
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # 최상위 NavigationLayout 생성
        self.navigation_layout = MDNavigationLayout()

        # ScreenManager + 메인 화면
        self.screen_manager = ScreenManager()
        main_screen = MDScreen()
        main_box = MDBoxLayout(orientation="vertical")

        # 툴바 생성
        self.toolbar = MDTopAppBar(
            title="작업확인서 생성기",
            md_bg_color=self.theme_cls.primary_color,
            specific_text_color=[1, 1, 1, 1],
            left_action_items=[["menu", lambda x: self.toggle_nav_drawer()]],
            right_action_items=[["refresh", self.reset_form]],
        )
        main_box.add_widget(self.toolbar)
        # 한 프레임 뒤에 툴바의 내부 label_title에 한글 폰트 적용
        Clock.schedule_once(self.set_toolbar_font, 0)

        # 스크롤뷰 + 입력 필드
        scroll = MDScrollView()
        self.content_layout = MDBoxLayout(
            orientation="vertical", padding=[dp(16), dp(24)], spacing=dp(16), adaptive_height=True
        )
        self.create_input_fields()
        scroll.add_widget(self.content_layout)
        main_box.add_widget(scroll)

        main_screen.add_widget(main_box)
        self.screen_manager.add_widget(main_screen)

        # 좌측 Navigation Drawer (생성된 문서 리스트)
        self.nav_drawer = MDNavigationDrawer()
        self.nav_list = MDBoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        self.nav_drawer.add_widget(self.nav_list)

        # NavigationLayout에 ScreenManager와 Drawer 추가
        self.navigation_layout.add_widget(self.screen_manager)
        self.navigation_layout.add_widget(self.nav_drawer)

        # 빌드 직후에, 과거 생성된 문서 목록을 로드
        Clock.schedule_once(lambda dt: self.populate_nav_list(), 0)

        return self.navigation_layout

    # 툴바 토글 (햄버거 버튼 클릭)
    def toggle_nav_drawer(self):
        # Drawer를 열기 전마다 최신 목록으로 갱신
        self.populate_nav_list()
        self.nav_drawer.set_state("open")

    # 툴바 내부 Label에 한글 폰트 적용
    def set_toolbar_font(self, *args):
        try:
            self.toolbar.ids.label_title.font_name = "malgun"
        except Exception as e:
            print("⚠️ 툴바 폰트 적용 실패:", e)

    # 입력 필드 및 생성 버튼 추가
    def create_input_fields(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.inputs = {}
        fields = [
            ("작업일자 (YYYY-MM-DD)", "work_date", "single", today),
            ("현장명", "location_04", "single", ""),
            ("장비명", "device_05", "single", ""),
            ("차량번호", "carno_06", "single", ""),
            ("작업시작시간 (HH:MM)", "start_time", "single", "09:00"),
            ("작업종료시간 (HH:MM)", "end_time", "single", "18:00"),
            ("작업내용", "work_content_13", "multiline", ""),
            ("확인일자 (YYYY-MM-DD)", "confirm_date", "single", today),
            ("차단팀장명", "cert_17", "single", ""),
            ("현장책임자명", "cert_18", "single", ""),
        ]

        for label, key, field_type, default_value in fields:
            tf = DynamicMDTextField(
                hint_text=label,
                text=default_value,
                mode="rectangle",
                font_name="malgun",
                size_hint_y=None,
                height=dp(56) if field_type == "single" else dp(120),
                multiline=(field_type == "multiline"),
            )
            self.inputs[key] = tf
            self.content_layout.add_widget(tf)

        btn = MDRaisedButton(
            text="DOCX 생성 및 저장",
            on_release=self.generate_docx,
            font_name="malgun",
            size_hint=(1, None),
            height=dp(56),
            md_bg_color=self.theme_cls.primary_color,
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1],
        )
        self.content_layout.add_widget(btn)

    # DOCX 생성 → 폴더 및 파일명 규칙(날짜_현장명_작업확인서.docx) → 이미지 변환 → 네비게이션 리스트 업데이트
    def generate_docx(self, instance):
        try:
            raw = {k: v.text.strip() for k, v in self.inputs.items()}
            required_fields = ["work_date", "location_04", "device_05", "start_time", "end_time"]
            for field in required_fields:
                if not raw[field]:
                    raise ValueError(f"필수 항목 '{field}'을 입력해주세요")

            # 저장 폴더 및 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            location = raw["location_04"]
            safe_location = sanitize_filename(location)
            folder_name = f"{timestamp}_{safe_location}"
            save_dir = os.path.join(SAVE_ROOT, folder_name)
            os.makedirs(save_dir, exist_ok=True)

            docx_filename = f"{folder_name}_작업확인서.docx"
            docx_path = os.path.join(save_dir, docx_filename)
            img_path = os.path.join(save_dir, f"{folder_name}_작업확인서_preview.png")

            # DOCX 생성
            doc = DocxTemplate("작업확인서.docx")
            context = self.create_context(raw)
            doc.render(context)
            doc.save(docx_path)

            # 이미지 변환 (첫 페이지 미리보기)
            if convert_docx_to_image(docx_path, img_path):
                self.show_success_dialog(f"파일 저장 완료:\n{save_dir}")
            else:
                self.show_error_dialog("이미지 생성에 실패했습니다")

        except Exception as e:
            self.show_error_dialog(str(e))

    # DOCX 양식에 필요한 Context 생성
    def create_context(self, raw):
        def parse_date(d_str):
            dt = datetime.strptime(d_str, "%Y-%m-%d")
            return dt.strftime("%y"), dt.strftime("%m"), dt.strftime("%d")

        yr_01, mm_02, dd_03 = parse_date(raw["work_date"])
        yy_14, mm_15, dd_16 = parse_date(raw["confirm_date"])
        t_start = datetime.strptime(raw["start_time"], "%H:%M")
        t_end = datetime.strptime(raw["end_time"], "%H:%M")
        t_diff = t_end - t_start
        if t_diff.total_seconds() < 0:
            raise ValueError("종료시간이 시작시간보다 빠릅니다")
        total_min = int(t_diff.total_seconds() // 60)
        hr_11, min_12 = divmod(total_min, 60)

        return {
            "yr_01": yr_01,
            "mm_02": mm_02,
            "dd_03": dd_03,
            "location_04": raw["location_04"],
            "device_05": raw["device_05"],
            "carno_06": raw["carno_06"],
            "hr_07": t_start.strftime("%H"),
            "min_08": t_start.strftime("%M"),
            "hr_09": t_end.strftime("%H"),
            "min_10": t_end.strftime("%M"),
            "hr_11": str(hr_11),
            "min_12": f"{min_12:02}",
            "work_content_13": raw["work_content_13"],
            "yy_14": yy_14,
            "mm_15": mm_15,
            "dd_16": dd_16,
            "cert_17": raw["cert_17"],
            "cert_18": raw["cert_18"],
        }

    # Navigation Drawer에 아이템(문서 제목 + 미리보기 아이콘) 추가
    def update_nav_list(self, filename, img_path, docx_path):
        # 클릭 시 preview_document 호출
        item = OneLineAvatarIconListItem(
            text=filename, on_release=lambda x: self.preview_document(docx_path)
        )
        img = ImageLeftWidget(source=img_path)
        item.add_widget(img)
        self.nav_list.add_widget(item)

    # 목록 클릭 시 미리보기 다이얼로그 띄우기
    def preview_document(self, docx_path):
        # 네비게이션 드로어를 닫고 미리보기 다이얼로그 표시
        self.nav_drawer.set_state("close")
        img_path = docx_path.replace(".docx", "_preview.png")
        self.show_image_preview(img_path)

    def show_image_preview(self, img_path):
        # 이미지 크기와 다이얼로그 크기를 제한
        max_img_height = dp(400)
        dialog_height = dp(480)

        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(20),
            size_hint_y=None,
            height=dialog_height - dp(80)  # 버튼, 타이틀 높이 제외
        )
        try:
            preview = Image(
                source=img_path,
                size_hint=(1, None),
                height=max_img_height,
                allow_stretch=True,
                keep_ratio=True
            )
        except Exception:
            from kivymd.uix.label import MDLabel
            preview = MDLabel(text="미리보기를 로드할 수 없습니다", font_name="malgun")
        content.add_widget(preview)

        self.dialog = MDDialog(
            title="Document Preview",
            type="custom",
            content_cls=content,
            size_hint=(0.8, None),
            height=dialog_height,
            buttons=[
                MDRaisedButton(
                    text="닫기",
                    font_name="malgun",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ],
        )
        self.dialog.open()


    # 저장 폴더(날짜별/현장별) 스캔 → 네비게이션 드로어 목록 생성
    def populate_nav_list(self):
        # 기존 아이템 삭제
        self.nav_list.clear_widgets()

        # SAVE_ROOT 하위의 모든 폴더(각 문서가 저장된 폴더)를 가져와서 정렬
        try:
            all_folders = sorted(
                [d for d in os.listdir(SAVE_ROOT) if os.path.isdir(os.path.join(SAVE_ROOT, d))],
                reverse=True  # 최신 순
            )
            for folder_name in all_folders:
                folder_path = os.path.join(SAVE_ROOT, folder_name)
                # 폴더 내 .png(미리보기)와 .docx 파일을 찾음
                preview_img = None
                docx_file = None
                for f in os.listdir(folder_path):
                    if f.lower().endswith(".png") and "_preview" in f:
                        preview_img = os.path.join(folder_path, f)
                    if f.lower().endswith(".docx"):
                        docx_file = os.path.join(folder_path, f)
                if preview_img and docx_file:
                    # "YYYYMMDD_현장명_작업확인서.docx"으로 표시
                    display_name = os.path.basename(docx_file)
                    self.update_nav_list(display_name, preview_img, docx_file)
        except Exception as e:
            print(f"네비게이션 목록 갱신 중 오류: {e}")

    # 입력 필드 초기화
    def reset_form(self, instance):
        today = datetime.now().strftime("%Y-%m-%d")
        defaults = {
            "work_date": today,
            "confirm_date": today,
            "start_time": "09:00",
            "end_time": "18:00",
        }
        for key, tf in self.inputs.items():
            tf.text = defaults.get(key, "")

    # 성공 다이얼로그 (한글 깨짐 방지)
    def show_success_dialog(self, message):
        self.dialog = MDDialog(
            title="성공",
            text=message,
            buttons=[MDRaisedButton(text="확인", font_name="malgun", on_release=lambda x: self.dialog.dismiss())],
        )
        # 다이얼로그 열린 직후 내부 레이블에 한글 폰트 적용
        Clock.schedule_once(self._set_dialog_font_after_open, 0)
        self.dialog.open()

    # 오류 다이얼로그 (한글 깨짐 방지)
    def show_error_dialog(self, message):
        self.dialog = MDDialog(
            title="오류",
            text=message,
            buttons=[MDRaisedButton(text="확인", font_name="malgun", on_release=lambda x: self.dialog.dismiss())],
        )
        # 다이얼로그 열린 직후 내부 레이블에 한글 폰트 적용
        Clock.schedule_once(self._set_dialog_font_after_open, 0)
        self.dialog.open()

    # MDDialog가 완전히 렌더링된 후, 내부 Label에 malgun 폰트를 적용
    def _set_dialog_font_after_open(self, *args):
        try:
            self.dialog.ids.label_title.font_name = "malgun"
        except Exception:
            pass
        try:
            self.dialog.ids.text_label.font_name = "malgun"
        except Exception:
            pass

    # 다이얼로그용 확인 버튼 생성
    def create_dialog_button(self):
        return MDRaisedButton(
            text="확인", font_name="malgun", on_release=lambda x: self.dialog.dismiss()
        )


if __name__ == "__main__":
    WorkFormApp().run()
