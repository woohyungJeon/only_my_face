import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import os

# [아이콘 설정]
ICON_FACE   = "👤"
ICON_IMAGE  = "🖼"
ICON_BLUR   = "✦"
ICON_SAVE   = "↓"
ICON_SUN    = "☀"
ICON_MOON   = "☾"
ICON_DELETE = "✕"
ICON_ADD    = "+"

# =================================================================
# 1. 인물 등록 팝업 (자동 크기 조절 버전)
# =================================================================
class AddPersonDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("얼굴 등록")
        self.resizable(False, False)
        self.grab_set()

        self.result_name  = None
        self.result_paths = None

        # [자동 레이아웃 핵심] 컬럼 가중치 설정
        self.grid_columnconfigure(0, weight=1)

        # --- 이름 입력 섹션 ---
        ctk.CTkLabel(self, text="이름", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=("gray20", "gray90"), anchor="w"
        ).grid(row=0, column=0, padx=25, pady=(25, 5), sticky="w")

        self.name_entry = ctk.CTkEntry(self, placeholder_text="이름을 입력하세요", height=38)
        self.name_entry.grid(row=1, column=0, padx=25, sticky="ew")

        # --- 사진 선택 섹션 ---
        self.photo_btn = ctk.CTkButton(
            self, text=f"{ICON_IMAGE}  사진 선택",
            command=self._select_photos, height=38,
            fg_color="transparent", border_width=1,
            text_color=("gray20", "gray90")
        )
        self.photo_btn.grid(row=2, column=0, padx=25, pady=(15, 0), sticky="ew")

        self.photo_label = ctk.CTkLabel(
            self, text="선택된 파일 없음", font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray60")
        )
        self.photo_label.grid(row=3, column=0, pady=(5, 0))

        # --- 하단 버튼 섹션 (취소/등록) ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=25, pady=(25, 30), sticky="ew") # 하단 pady를 넉넉히 주어 잘림 방지
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(btn_frame, text="취소", command=self.destroy, height=38,
                      fg_color="transparent", border_width=1,
                      text_color=("gray20", "gray90")
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(btn_frame, text="등록", command=self._confirm, height=38
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        # ---------------------------------------------------------
        # [마법의 자동 크기 & 중앙 정렬 로직]
        # ---------------------------------------------------------
        self.update_idletasks() # 내부 위젯 크기를 먼저 계산하게 함

        # 내용물에 필요한 가로/세로 크기를 자동으로 가져옴
        req_w = self.winfo_reqwidth()
        req_h = self.winfo_reqheight()

        # 부모 창의 위치와 크기를 고려하여 정중앙 좌표 계산
        pos_x = parent.winfo_x() + (parent.winfo_width()  - req_w) // 2
        pos_y = parent.winfo_y() + (parent.winfo_height() - req_h) // 2

        # 계산된 크기와 위치를 한 번에 적용 (잘림 현상 원천 봉쇄)
        self.geometry(f"{req_w}x{req_h}+{pos_x}+{pos_y}")
        self.lift()
        self.focus_force()

    def _select_photos(self):
        paths = filedialog.askopenfilenames(title="사진 선택", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp")])
        if paths:
            self.result_paths = list(paths)
            self.photo_btn.configure(text=f"{ICON_IMAGE}  {len(paths)}장 선택됨")
            names = [os.path.basename(p) for p in paths[:2]]
            suffix = "..." if len(paths) > 2 else ""
            self.photo_label.configure(text=", ".join(names) + suffix, text_color=("gray20", "gray90"))

    def _confirm(self):
        name = self.name_entry.get().strip()
        if not name: self.name_entry.configure(border_color="red"); return
        if not self.result_paths: self.photo_btn.configure(border_color="red"); return
        self.result_name = name
        self.destroy()

# =================================================================
# 2. 인물 카드 위젯 (컬러 대응 버전)
# =================================================================
class PersonCard(ctk.CTkFrame):
    def __init__(self, parent, name, photo_paths, on_delete, **kwargs):
        # 배경색을 라이트(밝은회색)/다크(진한회색) 자동 대응
        super().__init__(parent, corner_radius=12, fg_color=("gray90", "gray16"), **kwargs)
        self.grid_columnconfigure(1, weight=1)

        # 썸네일 생성
        img = Image.open(photo_paths[0])
        img.thumbnail((48, 48))
        ctk_thumb = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
        self._ref = ctk_thumb # 가비지 컬렉션 방지

        ctk.CTkLabel(self, image=ctk_thumb, text="").grid(row=0, column=0, rowspan=2, padx=12, pady=12)

        # 텍스트 색상을 모드에 따라 반전
        ctk.CTkLabel(self, text=name, font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=("black", "white"), anchor="w"
        ).grid(row=0, column=1, sticky="sw", pady=(12, 0))

        ctk.CTkLabel(self, text=f"이미지 {len(photo_paths)}장", font=ctk.CTkFont(size=11),
                     text_color=("gray40", "gray60"), anchor="w"
        ).grid(row=1, column=1, sticky="nw", pady=(0, 12))

        ctk.CTkButton(self, text=ICON_DELETE, width=28, height=28, corner_radius=8,
                      fg_color="transparent", border_width=1, border_color=("gray70", "gray30"),
                      text_color=("gray30", "gray70"), hover_color=("gray80", "gray25"),
                      command=on_delete).grid(row=0, column=2, rowspan=2, padx=12)

# =================================================================
# 3. 메인 앱 (영역별 주석 포함)
# =================================================================
class FaceBlurApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Face Guard AI - Privacy Protection")
        self.geometry("1000x720")
        self.minsize(900, 650)

        # [상태 데이터]
        self._mode = "dark"
        self.registered_people = []
        self.person_cards = []
        self.target_image_paths = []
        self.result_images = []
        self.result_ctk_images = []

        self._build_ui()

    def _build_ui(self):
        """전체 UI 레이아웃 구성"""
        self.grid_columnconfigure(0, weight=0) # 좌측 사이드바
        self.grid_columnconfigure(1, weight=1) # 우측 결과창
        self.grid_rowconfigure(0, weight=1)

        # ---------------------------------------------------------
        # [A] 좌측 사이드바 패널
        # ---------------------------------------------------------
        self.sidebar = ctk.CTkFrame(self, corner_radius=0, width=380)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(4, weight=1) # 사람 목록 영역 확장
        self.sidebar.grid_propagate(False)

        # [사이드바-헤더]
        hdr = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=25, pady=(30, 5), sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="Face Guard", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=("black", "white")).grid(row=0, column=0, sticky="w")

        self.mode_btn = ctk.CTkButton(hdr, text=ICON_SUN, width=36, height=36, corner_radius=10,
                                      fg_color=("gray85", "gray25"), text_color=("black", "white"),
                                      command=self._toggle_mode)
        self.mode_btn.grid(row=0, column=1)

        ctk.CTkLabel(self.sidebar, text="비식별화 처리 시스템", font=ctk.CTkFont(size=12),
                     text_color=("gray40", "gray60")).grid(row=1, column=0, padx=25, pady=(0, 20), sticky="w")

        # [사이드바-인물 등록 섹션]
        face_hdr = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        face_hdr.grid(row=2, column=0, padx=25, sticky="ew")
        face_hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(face_hdr, text=f"{ICON_FACE}  얼굴 등록", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=("black", "white")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(face_hdr, text=ICON_ADD, width=32, height=32, corner_radius=8,
                      command=self._open_add_person).grid(row=0, column=1)

        # [사이드바-인물 목록 스크롤]
        self.people_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.people_scroll.grid(row=4, column=0, padx=10, pady=(10, 0), sticky="nsew")
        self.people_scroll.grid_columnconfigure(0, weight=1)
        # 스크롤바 숨기기 기술
        self.after(100, lambda: self.people_scroll._scrollbar.grid_remove())

        self.empty_label = ctk.CTkLabel(self.people_scroll, text="등록된 얼굴이 없습니다",
                                        font=ctk.CTkFont(size=12), text_color=("gray50", "gray60"))
        self.empty_label.grid(row=0, column=0, pady=30)

        # [사이드바-하단 제어부]
        ctrl_frame = ctk.CTkFrame(self.sidebar, fg_color=("gray85", "gray20"), corner_radius=15)
        ctrl_frame.grid(row=5, column=0, padx=20, pady=25, sticky="ew")
        ctrl_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(ctrl_frame, text=f"{ICON_IMAGE}  대상 이미지 선택", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=("black", "white")).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.target_btn = ctk.CTkButton(ctrl_frame, text="파일 불러오기", command=self._select_target,
                                        height=35, fg_color="transparent", border_width=1)
        self.target_btn.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.target_info = ctk.CTkLabel(ctrl_frame, text="선택된 파일 없음", font=ctk.CTkFont(size=11),
                                        text_color=("gray50", "gray60"))
        self.target_info.grid(row=2, column=0, padx=15, pady=(0, 10))

        self.start_btn = ctk.CTkButton(ctrl_frame, text=f"{ICON_BLUR}  프로세스 시작", height=45,
                                       font=ctk.CTkFont(size=14, weight="bold"), state="disabled",
                                       command=self._start_blur)
        self.start_btn.grid(row=3, column=0, padx=15, pady=(10, 15), sticky="ew")

        # ---------------------------------------------------------
        # [B] 우측 결과 미리보기 영역
        # ---------------------------------------------------------
        self.right = ctk.CTkFrame(self, corner_radius=15, fg_color=("white", "gray12"))
        self.right.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.right.grid_columnconfigure(0, weight=1)
        self.right.grid_rowconfigure(1, weight=1)

        # [결과창-헤더]
        rhdr = ctk.CTkFrame(self.right, fg_color="transparent")
        rhdr.grid(row=0, column=0, padx=25, pady=(20, 10), sticky="ew")
        rhdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(rhdr, text="Preview Result", font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=("black", "white")).grid(row=0, column=0, sticky="w")

        self.save_btn = ctk.CTkButton(rhdr, text=f"{ICON_SAVE}  전체 저장", command=self._save_results,
                                      width=110, height=32, state="disabled", fg_color="#27ae60", hover_color="#219150")
        self.save_btn.grid(row=0, column=1)

        # [결과창-스크롤 영역]
        self.result_scroll = ctk.CTkScrollableFrame(self.right, fg_color="transparent")
        self.result_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.result_scroll.grid_columnconfigure(0, weight=1)
        self.after(100, lambda: self.result_scroll._scrollbar.grid_remove())

        self.placeholder = ctk.CTkLabel(self.result_scroll, text="이미지를 분석하면 여기에 표시됩니다",
                                        font=ctk.CTkFont(size=13), text_color=("gray50", "gray60"))
        self.placeholder.grid(row=0, column=0, pady=100)

    # ---------------------------------------------------------
    # [C] 핵심 로직 함수들
    # ---------------------------------------------------------

    def _toggle_mode(self):
        if self._mode == "dark":
            self._mode = "light"
            ctk.set_appearance_mode("light")
            self.mode_btn.configure(text=ICON_MOON)
        else:
            self._mode = "dark"
            ctk.set_appearance_mode("dark")
            self.mode_btn.configure(text=ICON_SUN)

    def _open_add_person(self):
        dialog = AddPersonDialog(self)
        self.wait_window(dialog)
        if dialog.result_name and dialog.result_paths:
            self._add_person(dialog.result_name, dialog.result_paths)

    def _add_person(self, name, paths):
        self.registered_people.append({"name": name, "paths": paths})
        if self.empty_label.winfo_exists(): self.empty_label.destroy()

        idx = len(self.person_cards)
        card = PersonCard(self.people_scroll, name, paths, on_delete=lambda i=idx: self._delete_person(i))
        card.grid(row=idx, column=0, pady=(0, 8), sticky="ew")
        self.person_cards.append(card)
        self._check_ready()

    def _delete_person(self, idx):
        self.person_cards[idx].destroy()
        self.person_cards.pop(idx)
        self.registered_people.pop(idx)

        if not self.registered_people:
            self._build_empty_label()

        for i, card in enumerate(self.person_cards):
            card.grid(row=i, column=0, pady=(0, 8), sticky="ew")
        self._check_ready()

    def _build_empty_label(self):
        self.empty_label = ctk.CTkLabel(self.people_scroll, text="등록된 얼굴이 없습니다", text_color=("gray50", "gray60"))
        self.empty_label.grid(row=0, column=0, pady=30)

    def _select_target(self):
        paths = filedialog.askopenfilenames(title="이미지 선택", filetypes=[("Image Files", "*.jpg *.png *.bmp")])
        if paths:
            self.target_image_paths = list(paths)
            self.target_info.configure(text=f"{len(paths)}개 파일 선택됨", text_color="#3498db")
            self._check_ready()

    def _check_ready(self):
        ready = bool(self.registered_people and self.target_image_paths)
        self.start_btn.configure(state="normal" if ready else "disabled")

    def _start_blur(self):
        """[AI 분석 및 블러 처리 메인 로직]"""
        for w in self.result_scroll.winfo_children(): w.destroy()
        self.result_images = []
        self.result_ctk_images = []
        self.start_btn.configure(text="분석 중...", state="disabled")
        self.update()

        try:
            for i, path in enumerate(self.target_image_paths):
                img = Image.open(path)
                # -------------------------------------------------------
                # AI 처리 로직 삽입 지점 (현재는 원본 유지)
                # -------------------------------------------------------
                self.result_images.append(img)

                thumb = img.copy()
                thumb.thumbnail((650, 500))

                card = ctk.CTkFrame(self.result_scroll, corner_radius=15, fg_color=("gray95", "gray16"))
                card.grid(row=i, column=0, pady=(0, 15), sticky="ew")
                card.grid_columnconfigure(0, weight=1)

                ctk_img = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
                self.result_ctk_images.append(ctk_img)

                ctk.CTkLabel(card, image=ctk_img, text="").grid(row=0, column=0, padx=20, pady=20)
                ctk.CTkLabel(card, text=os.path.basename(path), font=ctk.CTkFont(size=11),
                             text_color=("gray50", "gray60")).grid(row=1, column=0, pady=(0, 15))

            self.save_btn.configure(state="normal")
            self.start_btn.configure(text=f"{ICON_BLUR} 프로세스 완료", state="normal")
        except Exception as e:
            self.start_btn.configure(text="오류 발생", state="normal")
            print(f"Error: {e}")

    def _save_results(self):
        folder = filedialog.askdirectory(title="결과물 저장 폴더 선택")
        if folder:
            for i, img in enumerate(self.result_images):
                img.save(os.path.join(folder, f"blur_result_{i}.jpg"))
            print("저장 완료")

if __name__ == "__main__":
    app = FaceBlurApp()
    app.mainloop()