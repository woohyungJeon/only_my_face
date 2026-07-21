"""Only My Face - local, batch face anonymizer.

All processing stays on this computer.  The first time it runs, InsightFace
downloads the buffalo_l model weights (a one-time ~326 MB download).
"""

from __future__ import annotations

import os
import queue
import sys
import threading
import traceback
import json
import base64
import io
import ctypes
import shutil
import webbrowser
import urllib.request
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import customtkinter as ctk
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter, ImageOps
from tkinter import filedialog, messagebox

# When launched through pythonw.exe there is no stdout/stderr. InsightFace uses
# tqdm while downloading its model and tqdm requires a writable stream.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None


APP_NAME = "Only My Face"
# Keep in sync with AppVersion in installer/OnlyMyFace.iss and version.txt.
APP_VERSION = "1.1.1"
# A tiny text file in the repo whose first line is the latest version. The update
# check is best-effort: any network error is silently ignored (offline is fine).
VERSION_URL = "https://raw.githubusercontent.com/PlumpyCarrot/only_my_face/main/version.txt"
RELEASES_URL = "https://github.com/PlumpyCarrot/only_my_face/releases/latest"
WINDOWS_APP_ID = "OnlyMyFace.LocalPrivacyTool.1"
IMAGE_TYPES = [("Image files", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff")]
# One accent color, matched to the app's shield logo. Everything else in the
# UI stays grayscale so the accent is the only thing that draws the eye.
ACCENT = "#7C3AED"
ACCENT_HOVER = "#6D28D9"
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSETS_DIR = RESOURCE_DIR / "assets"
# User-created data must never live beside an installed program (Program Files is
# read-only for normal users).  Keeping it in LocalAppData also makes upgrades safe.
DATA_DIR = Path(os.environ.get("LOCALAPPDATA", RESOURCE_DIR)) / "OnlyMyFace"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = DATA_DIR / "only_my_face_settings.json"
EXEMPTIONS_PATH = DATA_DIR / "only_my_face_exemptions.json"
LOG_PATH = DATA_DIR / "only_my_face.log"
# Pretendard Bold renders inconsistently in Tk on some Windows setups.  Bundle
# the Regular face only and use size/colour for hierarchy instead of fake bold.
FONT_FILES = (ASSETS_DIR / "fonts" / "Pretendard-Regular.otf",)
# A bundled illustrated sample (not a real person) used for the live settings
# preview.  SAMPLE_FACE_BOX is the face region on that 300x360 image.
SAMPLE_FACE_PATH = ASSETS_DIR / "sample-face.png"
SAMPLE_FACE_BOX = (78, 108, 222, 258)
EXEMPTION_MATCH_THRESHOLD = 0.45
SECONDARY_TEXT = ("#3D3D4D", "#C2C2D0")
MUTED_TEXT = ("#595969", "#AEAEBD")
PRIMARY_TEXT = ("#171923", "#F5F5FA")

# Keep existing development-version preferences and registered people when the
# app moves to the installer-safe LocalAppData location.
for legacy_name, destination in (("only_my_face_settings.json", SETTINGS_PATH), ("only_my_face_exemptions.json", EXEMPTIONS_PATH)):
    legacy_path = Path(__file__).with_name(legacy_name)
    if not destination.exists() and legacy_path.exists():
        try:
            shutil.copy2(legacy_path, destination)
        except OSError:
            pass

# The installer pre-populates this read-only folder with buffalo_l. Development
# mode falls back to a user-writable cache and downloads it once when needed.
BUNDLED_MODEL_DIR = RESOURCE_DIR / "models" / "insightface"
LEGACY_MODEL_DIR = Path.home() / ".insightface"
MODEL_ROOT = (
    BUNDLED_MODEL_DIR
    if BUNDLED_MODEL_DIR.exists()
    else LEGACY_MODEL_DIR
    if LEGACY_MODEL_DIR.exists()
    else DATA_DIR / "insightface"
)

if os.name == "nt":
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, WINDOWS_APP_ID)
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(None, "Only My Face is already running.", APP_NAME, 0x30)
        raise SystemExit(0)


def _register_app_fonts() -> None:
    """Temporarily register bundled Pretendard on Windows; no font install needed."""
    if os.name != "nt":
        return
    for font_path in FONT_FILES:
        if font_path.exists():
            ctypes.windll.gdi32.AddFontResourceExW(str(font_path), 0x10, None)


_register_app_fonts()
ctk.ThemeManager.theme["CTkFont"]["family"] = "Pretendard"


@dataclass
class ProcessedImage:
    source: Path
    image: Image.Image
    face_count: int
    masked_count: int
    exempted_count: int


class OnlyMyFaceApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.appearance_mode = self._load_appearance_mode()
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_NAME} v{APP_VERSION} — Local face anonymizer")
        self.icon_path = ASSETS_DIR / "only-my-face.ico"
        self.geometry("1180x760")
        self.minsize(960, 650)

        self.image_paths: list[Path] = []
        self.results: list[ProcessedImage] = []
        self.preview_refs: list[ctk.CTkImage] = []
        self.worker_messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.processing = False
        self.exempt_people = self._load_exempt_people()

        self.style_var = ctk.StringVar(value="모자이크")
        self.preset_var = ctk.StringVar(value="보통")
        self.strength_var = ctk.IntVar(value=18)
        self.padding_var = ctk.IntVar(value=20)
        self.threshold_var = ctk.DoubleVar(value=0.35)
        self._sample_face = self._load_sample_face()
        self._results_mode = "preview"
        self._preview_after: str | None = None
        self._build_ui()
        self._apply_window_icon()
        # Live-update the settings preview whenever an effect-related control moves.
        for effect_var in (self.style_var, self.strength_var, self.padding_var):
            effect_var.trace_add("write", self._on_setting_changed)
        self._update_result: str | None = None
        self.after(2000, self._check_for_update)

    @staticmethod
    def _load_sample_face() -> Image.Image | None:
        try:
            with Image.open(SAMPLE_FACE_PATH) as sample:
                return sample.convert("RGB")
        except Exception:
            return None

    def _check_for_update(self) -> None:
        threading.Thread(target=self._update_worker, daemon=True).start()
        self.after(1000, self._poll_update_result)

    def _update_worker(self) -> None:
        try:
            request = urllib.request.Request(VERSION_URL, headers={"User-Agent": "OnlyMyFace"})
            with urllib.request.urlopen(request, timeout=6) as response:
                self._update_result = response.read().decode("utf-8").strip().splitlines()[0].strip()
        except Exception:
            self._update_result = ""  # checked, but offline or unavailable — stay quiet

    def _poll_update_result(self) -> None:
        if self._update_result is None:
            self.after(1000, self._poll_update_result)
            return
        latest = self._update_result
        if latest and self._is_newer_version(latest, APP_VERSION):
            self.update_button.configure(text=f"● 새 버전 {latest}")
            self.update_button.grid()
            self._append_log(f"새 버전 {latest} 있음 (현재 {APP_VERSION}) — 릴리스에서 받으세요.")

    @staticmethod
    def _is_newer_version(latest: str, current: str) -> bool:
        def parts(version: str) -> list[int]:
            numbers = []
            for chunk in version.split("."):
                digits = "".join(ch for ch in chunk if ch.isdigit())
                numbers.append(int(digits) if digits else 0)
            return numbers
        return parts(latest) > parts(current)

    def _apply_window_icon(self) -> None:
        try:
            # iconbitmap sets the real Win32 HICON, which is what the taskbar
            # button reads; setting it late (e.g. via `after`) can leave the
            # taskbar showing Windows' generic window icon instead.
            self.iconbitmap(str(self.icon_path.resolve()))
            self.wm_iconbitmap(default=str(self.icon_path.resolve()))
        except Exception:
            self._append_log("앱 창 아이콘을 적용하지 못했습니다.")

    def _apply_icon_to_dialog(self, dialog: ctk.CTkToplevel) -> None:
        try:
            dialog.iconbitmap(str(self.icon_path.resolve()))
        except Exception:
            pass

    @staticmethod
    def _load_appearance_mode() -> Literal["light", "dark"]:
        try:
            mode = json.loads(SETTINGS_PATH.read_text(encoding="utf-8")).get("appearance_mode")
            if mode in {"light", "dark"}:
                return mode
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        return "dark"

    def _toggle_appearance_mode(self) -> None:
        self.appearance_mode = "light" if self.appearance_mode == "dark" else "dark"
        ctk.set_appearance_mode(self.appearance_mode)
        self.theme_button.configure(text="☾" if self.appearance_mode == "light" else "☀")
        try:
            SETTINGS_PATH.write_text(json.dumps({"appearance_mode": self.appearance_mode}), encoding="utf-8")
        except OSError:
            self._append_log("테마 설정을 저장하지 못했습니다.")

    def _apply_preset(self, preset: str) -> None:
        presets = {
            "연하게": (10, 10, 0.45),
            "보통": (18, 20, 0.35),
            "강하게": (30, 30, 0.25),
        }
        strength, padding, sensitivity = presets[preset]
        self.strength_var.set(strength)
        self.padding_var.set(padding)
        self.threshold_var.set(sensitivity)
        self._append_log(f"처리 강도 프리셋 적용: {preset}")

    @staticmethod
    def _load_exempt_people() -> list[dict]:
        try:
            people = json.loads(EXEMPTIONS_PATH.read_text(encoding="utf-8"))
            return [person for person in people if person.get("name") and person.get("embeddings")]
        except (OSError, ValueError, json.JSONDecodeError):
            return []

    def _save_exempt_people(self) -> None:
        EXEMPTIONS_PATH.write_text(json.dumps(self.exempt_people, ensure_ascii=False), encoding="utf-8")

    def _update_exemption_button(self) -> None:
        self.exemption_button.configure(text=f"예외 인물 관리 ({len(self.exempt_people)})")

    @staticmethod
    def _encode_face_preview(image: Image.Image) -> str:
        thumb = image.copy()
        thumb.thumbnail((96, 96))
        buffer = io.BytesIO()
        thumb.save(buffer, "PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def _decode_face_preview(value: str) -> Image.Image | None:
        try:
            return Image.open(io.BytesIO(base64.b64decode(value))).convert("RGBA")
        except Exception:
            return None

    def _open_exemption_manager(self) -> None:
        if self.processing:
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("예외 인물 관리")
        dialog.geometry("480x480")
        dialog.transient(self)
        dialog.grab_set()
        self._apply_icon_to_dialog(dialog)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(dialog, text="예외 인물 관리", font=ctk.CTkFont(size=20)).grid(row=0, column=0, padx=22, pady=(22, 4), sticky="w")
        ctk.CTkLabel(dialog, text="등록된 사람은 모자이크 처리에서 자동 제외됩니다.", text_color=SECONDARY_TEXT).grid(row=1, column=0, padx=22, pady=(0, 12), sticky="w")
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.grid(row=2, column=0, padx=16, pady=4, sticky="nsew")
        preview_refs: list[ctk.CTkImage] = []

        def render() -> None:
            for child in scroll.winfo_children():
                child.destroy()
            if not self.exempt_people:
                ctk.CTkLabel(scroll, text="등록된 예외 인물이 없습니다.", text_color=SECONDARY_TEXT).pack(pady=50)
                scroll._scrollbar.grid_remove()
                return
            for index, person in enumerate(self.exempt_people):
                row = ctk.CTkFrame(scroll, corner_radius=12)
                row.pack(fill="x", pady=5)
                preview = self._decode_face_preview(person.get("preview", ""))
                if preview:
                    face_image = ctk.CTkImage(light_image=preview, dark_image=preview, size=(48, 48))
                    preview_refs.append(face_image)
                    ctk.CTkLabel(row, image=face_image, text="").pack(side="left", padx=(10, 8), pady=9)
                else:
                    ctk.CTkLabel(row, text="재등록", width=62, height=32, corner_radius=12, fg_color=("#FFE4E1", "#5A3030"), text_color=("#9F1D16", "#FFD2CC"), font=ctk.CTkFont(size=10)).pack(side="left", padx=(10, 8), pady=9)
                ctk.CTkLabel(row, text=person["name"], font=ctk.CTkFont(size=14)).pack(side="left", padx=14, pady=12)
                ctk.CTkLabel(row, text=f"라벨 {len(person['embeddings'])}개", text_color=SECONDARY_TEXT).pack(side="left", padx=4)
                def add_photos(i=index) -> None:
                    dialog.destroy()
                    self._register_exempt_person(person_index=i)

                def rename(i=index) -> None:
                    name_dialog = ctk.CTkInputDialog(text="새 이름을 입력하세요.", title="예외 인물 이름 수정")
                    new_name = name_dialog.get_input()
                    if new_name and new_name.strip():
                        self.exempt_people[i]["name"] = new_name.strip()
                        self._save_exempt_people()
                        render()

                def remove(i=index) -> None:
                    if messagebox.askyesno("예외 인물 삭제", f"‘{self.exempt_people[i]['name']}’을 삭제할까요?", parent=dialog):
                        self.exempt_people.pop(i)
                        self._save_exempt_people()
                        self._update_exemption_button()
                        render()
                controls = ctk.CTkFrame(row, fg_color="transparent")
                controls.pack(side="right", padx=10, pady=8)
                ctk.CTkButton(controls, text="사진 추가", width=70, height=30, fg_color="transparent", border_width=1, text_color=PRIMARY_TEXT, border_color=("#D0D2D9", "#50515F"), command=add_photos).pack(side="left", padx=(0, 5))
                ctk.CTkButton(controls, text="이름 수정", width=66, height=30, fg_color="transparent", border_width=1, text_color=PRIMARY_TEXT, border_color=("#D0D2D9", "#50515F"), command=rename).pack(side="left", padx=(0, 5))
                ctk.CTkButton(controls, text="삭제", width=54, height=30, fg_color="transparent", border_width=1, text_color=("#B42318", "#FFB4AB"), border_color=("#D0D2D9", "#50515F"), command=remove).pack(side="left")
            if len(self.exempt_people) <= 4:
                scroll._scrollbar.grid_remove()

        def add_person() -> None:
            dialog.destroy()
            self._register_exempt_person()

        render()
        ctk.CTkButton(dialog, text="+ 예외 인물 추가", command=add_person, height=40, fg_color=ACCENT, text_color="white").grid(row=3, column=0, padx=20, pady=18, sticky="ew")

    def _register_exempt_person(self, person_index: int | None = None) -> None:
        if self.processing:
            return
        if person_index is None:
            dialog = ctk.CTkInputDialog(text="이 사람은 모자이크하지 않습니다.", title="예외 인물 추가")
            name = dialog.get_input()
            if not name or not name.strip():
                return
            name = name.strip()
            title = "예외할 인물 사진 선택 (여러 장 가능)"
        else:
            name = self.exempt_people[person_index]["name"]
            title = f"‘{name}’에 추가할 사진 선택 (여러 장 가능)"
        paths = filedialog.askopenfilenames(title=title, filetypes=IMAGE_TYPES)
        if not paths:
            return
        self.processing = True
        self.process_button.configure(state="disabled")
        self.exemption_button.configure(state="disabled", text="얼굴 등록 중...")
        self._set_status("예외 인물의 얼굴 특징을 등록하는 중입니다. 처음에는 모델 다운로드가 필요할 수 있어요.", "busy")
        self._show_progress()
        action = "사진 추가" if person_index is not None else "등록"
        self._append_log(f"예외 인물 {action} 시작: {name} / 사진 {len(paths)}장")
        threading.Thread(target=self._register_worker, args=(name, [Path(path) for path in paths], person_index), daemon=True).start()
        self.after(100, self._read_worker_messages)

    @staticmethod
    def _make_analyzer(det_thresh: float = 0.35):
        available = ort.get_available_providers()
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if "CUDAExecutionProvider" in available else ["CPUExecutionProvider"]
        analyzer = FaceAnalysis(
            name="buffalo_l",
            root=str(MODEL_ROOT),
            allowed_modules=["detection", "recognition"],
            providers=providers,
        )
        analyzer.prepare(ctx_id=0 if "CUDAExecutionProvider" in providers else -1, det_size=(1280, 1280), det_thresh=det_thresh)
        return analyzer

    def _register_worker(self, name: str, paths: list[Path], person_index: int | None = None) -> None:
        try:
            analyzer = self._make_analyzer()
            candidates: list[dict] = []
            skipped: list[str] = []
            for path in paths:
                with Image.open(path) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                faces = analyzer.get(np.asarray(image))
                if not faces:
                    skipped.append(path.name)
                    continue
                for face_index, face in enumerate(faces, start=1):
                    x1, y1, x2, y2 = face.bbox.astype(int).tolist()
                    margin = int(max(x2 - x1, y2 - y1) * 0.2)
                    crop = image.crop((max(0, x1 - margin), max(0, y1 - margin), min(image.width, x2 + margin), min(image.height, y2 + margin)))
                    candidates.append({"source": path.name, "face_index": face_index, "crop": crop, "embedding": face.normed_embedding.astype(float).tolist()})
            if not candidates:
                raise ValueError("선택한 사진에서 등록할 얼굴을 찾지 못했습니다.")
            self.worker_messages.put(("registration_candidates", {"name": name, "candidates": candidates, "skipped": skipped, "person_index": person_index}))
        except Exception as error:
            self.worker_messages.put(("registration_error", f"{error}\n\n{traceback.format_exc()}"))

    def _open_face_label_dialog(self, name: str, candidates: list[dict], skipped: list[str], person_index: int | None = None) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"예외 인물 라벨링 — {name}")
        dialog.geometry("760x620")
        dialog.transient(self)
        dialog.grab_set()
        self._apply_icon_to_dialog(dialog)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(2, weight=1)
        heading = f"‘{name}’에 추가할 얼굴만 선택하세요" if person_index is not None else f"‘{name}’인 얼굴만 선택하세요"
        ctk.CTkLabel(dialog, text=heading, font=ctk.CTkFont(size=18)).grid(row=0, column=0, padx=22, pady=(20, 4), sticky="w")
        ctk.CTkLabel(dialog, text="사진마다 여러 얼굴이 보이면 본인 얼굴만 체크합니다. 선택한 얼굴 특징만 저장됩니다.", text_color=SECONDARY_TEXT).grid(row=1, column=0, padx=22, pady=(0, 12), sticky="w")
        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.grid(row=2, column=0, padx=16, pady=4, sticky="nsew")
        refs, selections = [], []
        for index, candidate in enumerate(candidates):
            cell = ctk.CTkFrame(scroll, corner_radius=12)
            cell.grid(row=index // 4, column=index % 4, padx=7, pady=7, sticky="nsew")
            thumb = candidate["crop"].copy()
            thumb.thumbnail((135, 135))
            image = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            refs.append(image)
            ctk.CTkLabel(cell, image=image, text="").pack(padx=10, pady=(10, 5))
            selected = ctk.BooleanVar(value=False)
            selections.append(selected)
            ctk.CTkCheckBox(cell, text=f"{candidate['source']} · 얼굴 {candidate['face_index']}", variable=selected, font=ctk.CTkFont(size=10)).pack(padx=8, pady=(0, 9))

        def finish() -> None:
            embeddings = [candidate["embedding"] for candidate, selected in zip(candidates, selections) if selected.get()]
            if not embeddings:
                messagebox.showwarning("얼굴 선택 필요", "등록할 얼굴을 한 개 이상 선택하세요.", parent=dialog)
                return
            selected_candidate = next(candidate for candidate, selected in zip(candidates, selections) if selected.get())
            if person_index is None:
                self.exempt_people.append({"name": name, "embeddings": embeddings, "preview": self._encode_face_preview(selected_candidate["crop"])})
            else:
                person = self.exempt_people[person_index]
                person["embeddings"].extend(embeddings)
                if not person.get("preview"):
                    person["preview"] = self._encode_face_preview(selected_candidate["crop"])
            self._save_exempt_people()
            self.processing = False
            self.exemption_button.configure(state="normal")
            self._update_exemption_button()
            self.process_button.configure(state="normal" if self.image_paths else "disabled")
            skipped_text = f" / 얼굴 없음 {len(skipped)}장" if skipped else ""
            action = "사진 추가 완료" if person_index is not None else "등록 완료"
            self.status.configure(text=f"예외 인물 ‘{name}’ {action} — 선택 얼굴 {len(embeddings)}개{skipped_text}")
            self._append_log(f"예외 인물 {action}: {name} / 선택 얼굴 {len(embeddings)}개{skipped_text}")
            dialog.destroy()

        def cancel() -> None:
            self.processing = False
            self.exemption_button.configure(state="normal")
            self._update_exemption_button()
            self.process_button.configure(state="normal" if self.image_paths else "disabled")
            self.status.configure(text="예외 인물 등록을 취소했습니다.")
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        ctk.CTkButton(dialog, text="선택한 얼굴 등록", command=finish, height=40, fg_color=ACCENT, text_color="white").grid(row=3, column=0, padx=22, pady=16, sticky="e")

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=312, corner_radius=0, fg_color=("#F7F7F8", "#121212"))
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(5, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=22, pady=(18, 12), sticky="ew")
        ctk.CTkLabel(brand, text="◉  ONLY MY FACE", font=ctk.CTkFont(size=18), text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(brand, text="사진은 PC 밖으로 나가지 않아요", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT).pack(anchor="w", pady=(5, 0))

        upload = ctk.CTkFrame(sidebar, corner_radius=16, fg_color=("#EFEFF2", "#1B1B20"))
        upload.grid(row=1, column=0, padx=18, pady=(0, 12), sticky="ew")
        ctk.CTkLabel(upload, text="사진 추가", font=ctk.CTkFont(size=15)).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(upload, text="여러 장을 한 번에 선택할 수 있어요.", font=ctk.CTkFont(size=11), text_color=SECONDARY_TEXT).pack(anchor="w", padx=14)
        ctk.CTkButton(upload, text="파일 선택", command=self.select_images, height=34, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(sidebar, text="처리 설정", font=ctk.CTkFont(size=15)).grid(row=2, column=0, padx=22, pady=(0, 5), sticky="w")
        settings = ctk.CTkFrame(sidebar, fg_color="transparent")
        settings.grid(row=3, column=0, padx=18, pady=(0, 2), sticky="ew")
        settings.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(settings, text="효과", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        ctk.CTkSegmentedButton(settings, values=["모자이크", "블러"], variable=self.style_var, height=30, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER).grid(row=1, column=0, pady=(3, 7), sticky="ew")
        ctk.CTkLabel(settings, text="처리 강도", font=ctk.CTkFont(size=12)).grid(row=2, column=0, sticky="w")
        ctk.CTkSegmentedButton(settings, values=["연하게", "보통", "강하게"], variable=self.preset_var, command=self._apply_preset, height=30, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER).grid(row=3, column=0, pady=(3, 7), sticky="ew")
        self._slider(settings, 5, "효과 강도", self.strength_var, 8, 40, "픽셀 크기 / 흐림 정도")
        self._slider(settings, 8, "얼굴 주변 여백", self.padding_var, 0, 45, "얼굴 박스보다 넓게 처리")
        self._slider(settings, 11, "검출 민감도", self.threshold_var, 0.15, 0.70, "낮을수록 더 많은 얼굴 감지", step=0.01)

        self.file_count = ctk.CTkLabel(sidebar, text="선택한 사진 없음", font=ctk.CTkFont(size=12), text_color=SECONDARY_TEXT)
        self.file_count.grid(row=5, column=0, padx=22, pady=(4, 8), sticky="sw")
        self.process_button = ctk.CTkButton(sidebar, text="모든 얼굴 가리기", command=self.start_processing, height=48, font=ctk.CTkFont(size=15), fg_color=ACCENT, hover_color=ACCENT_HOVER, state="disabled")
        self.process_button.grid(row=6, column=0, padx=18, pady=(0, 8), sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(sidebar, height=6, progress_color=ACCENT)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=7, column=0, padx=18, pady=(0, 16), sticky="ew")
        self.progress_bar.grid_remove()

        content = ctk.CTkFrame(self, corner_radius=0, fg_color=("#FFFFFF", "#101016"))
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, padx=30, pady=(28, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="결과 미리보기", font=ctk.CTkFont(size=24)).grid(row=0, column=0, sticky="w")
        button_style = {"fg_color": "transparent", "border_width": 1, "text_color": PRIMARY_TEXT, "border_color": ("#B9BBC8", "#555664"), "hover_color": ("#E9E9F1", "#2D2D3A")}
        self.exemption_button = ctk.CTkButton(header, text=f"예외 인물 관리 ({len(self.exempt_people)})", command=self._open_exemption_manager, width=138, height=36, **button_style)
        self.exemption_button.grid(row=0, column=1, sticky="e")
        self.save_button = ctk.CTkButton(header, text="결과 전체 저장", command=self.save_results, width=130, height=36, fg_color="transparent", border_width=1, border_color=ACCENT, text_color=ACCENT, hover_color=("#F1EBFC", "#241B38"), state="disabled")
        self.save_button.grid(row=0, column=2, padx=(8, 0), sticky="e")
        self.log_button = ctk.CTkButton(header, text="로그 보기", command=self._toggle_log, width=88, height=36, **button_style)
        self.log_button.grid(row=0, column=3, padx=(8, 0), sticky="e")
        theme_text = "☾" if self.appearance_mode == "light" else "☀"
        self.theme_button = ctk.CTkButton(header, text=theme_text, command=self._toggle_appearance_mode, width=40, height=36, font=ctk.CTkFont(size=17), **button_style)
        self.theme_button.grid(row=0, column=4, padx=(8, 0), sticky="e")
        self.update_button = ctk.CTkButton(header, text="● 새 버전 있음", command=lambda: webbrowser.open(RELEASES_URL), width=118, height=36, fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="white")
        self.update_button.grid(row=0, column=5, padx=(8, 0), sticky="e")
        self.update_button.grid_remove()
        self.status = ctk.CTkLabel(content, text="   사진을 추가하면 여기에 처리 결과가 표시됩니다.", font=ctk.CTkFont(size=13), text_color=SECONDARY_TEXT, anchor="w", corner_radius=8, fg_color="transparent")
        self.status.grid(row=1, column=0, padx=30, pady=(0, 10), sticky="ew", ipady=8)
        self.results_frame = ctk.CTkScrollableFrame(content, corner_radius=0, fg_color="transparent")
        self.results_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.log_frame = ctk.CTkFrame(content, corner_radius=12, fg_color=("#F1F1F3", "#1B1B20"))
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_box = ctk.CTkTextbox(self.log_frame, height=145, font=ctk.CTkFont(size=11), text_color=("#5A5A66", "#A6A6B2"), wrap="word")
        self.log_box.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.log_box.configure(state="disabled")
        self.log_visible = False
        self._enter_preview_mode()

    def _toggle_log(self) -> None:
        self.log_visible = not self.log_visible
        if self.log_visible:
            self.log_frame.grid(row=3, column=0, padx=20, pady=(0, 16), sticky="ew")
            self.log_button.configure(text="로그 닫기")
        else:
            self.log_frame.grid_remove()
            self.log_button.configure(text="로그 보기")

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as log_file:
                log_file.write(line)
        except OSError:
            pass

    def _slider(self, parent: ctk.CTkFrame, row: int, title: str, variable, low: float, high: float, helper: str, step: float = 1) -> None:
        line = ctk.CTkFrame(parent, fg_color="transparent")
        line.grid(row=row, column=0, sticky="ew")
        line.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(line, text=title, font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        value = ctk.CTkLabel(line, textvariable=variable, font=ctk.CTkFont(size=12), text_color=ACCENT)
        value.grid(row=0, column=1, sticky="e")
        ctk.CTkSlider(parent, from_=low, to=high, number_of_steps=round((high-low)/step), variable=variable, button_color=ACCENT, progress_color=ACCENT).grid(row=row+1, column=0, pady=(2, 0), sticky="ew")
        ctk.CTkLabel(parent, text=helper, font=ctk.CTkFont(size=10), text_color=MUTED_TEXT).grid(row=row+2, column=0, pady=(0, 6), sticky="w")

    def _show_progress(self) -> None:
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.grid()
        self.progress_bar.start()

    def _set_progress_fraction(self, current: int, total: int) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(current / total if total else 0)

    def _hide_progress(self) -> None:
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

    def _set_status(self, text: str, kind: str = "idle") -> None:
        # A colored bar (not emoji, which the bundled font renders as broken boxes).
        # The colored bar carries the emphasis, so the text stays a light regular
        # weight — bold here looked too heavy.
        styles = {
            "idle": {"fg": "transparent", "fg_text": SECONDARY_TEXT},
            "busy": {"fg": ("#EDE7FB", "#241B38"), "fg_text": ACCENT},
            "done": {"fg": ACCENT, "fg_text": "#FFFFFF"},
            "warn": {"fg": ("#FBE3E3", "#3A1B1B"), "fg_text": ("#B42318", "#FFB4AB")},
        }
        style = styles.get(kind, styles["idle"])
        self.status.configure(text="   " + text, fg_color=style["fg"], text_color=style["fg_text"], font=ctk.CTkFont(size=13))

    @staticmethod
    def _apply_effect(region: Image.Image, style: str, strength: int) -> Image.Image:
        strength = max(1, int(strength))
        if style == "블러":
            return region.filter(ImageFilter.GaussianBlur(radius=strength))
        small = region.resize((max(1, region.width // strength), max(1, region.height // strength)), Image.Resampling.BILINEAR)
        return small.resize(region.size, Image.Resampling.NEAREST)

    def _reset_results_columns(self, columns: int) -> None:
        self.results_frame.grid_columnconfigure(0, weight=1)
        for col in (1, 2):
            self.results_frame.grid_columnconfigure(col, weight=1 if col < columns else 0)

    def _enter_preview_mode(self) -> None:
        self._results_mode = "preview"
        self._render_preview_mode()

    def _render_preview_mode(self) -> None:
        self._clear_results()
        self.preview_refs = []
        self.settings_card_label = None
        self._reset_results_columns(3)
        if self.image_paths:
            # A photo is loaded — show its thumbnails, and hide the sample preview.
            self.results_frame._scrollbar.grid()
            self._render_selected_thumbnails(start_row=0)
        else:
            self.results_frame._scrollbar.grid_remove()
            self._build_settings_card(row=0)

    def _build_settings_card(self, row: int) -> None:
        card = ctk.CTkFrame(self.results_frame, corner_radius=16, fg_color=("#F4F4F6", "#1A1A1E"))
        card.grid(row=row, column=0, columnspan=3, padx=4, pady=(0, 14), sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="현재 설정 미리보기", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=18, pady=(16, 2), sticky="w")
        self.settings_card_label = ctk.CTkLabel(card, text="")
        self.settings_card_label.grid(row=1, column=0, padx=18, pady=(6, 4))
        self.settings_caption = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11), text_color=SECONDARY_TEXT)
        self.settings_caption.grid(row=2, column=0, padx=18, pady=(0, 8), sticky="w")
        ctk.CTkLabel(card, text="‘파일 선택’으로 사진을 추가하면 이 미리보기는 사라지고 선택한 사진이 표시됩니다.", font=ctk.CTkFont(size=11), text_color=MUTED_TEXT).grid(row=3, column=0, padx=18, pady=(0, 14), sticky="w")
        self._refresh_settings_card()

    def _render_selected_thumbnails(self, start_row: int) -> None:
        cols, cap = 3, 24
        shown = self.image_paths[:cap]
        ctk.CTkLabel(self.results_frame, text=f"선택한 사진 {len(self.image_paths)}장 · 아직 처리 전", font=ctk.CTkFont(size=13, weight="bold"), text_color=ACCENT).grid(row=start_row, column=0, columnspan=3, padx=6, pady=(4, 8), sticky="w")
        for index, path in enumerate(shown):
            try:
                with Image.open(path) as source:
                    try:
                        source.draft("RGB", (240, 240))
                    except Exception:
                        pass
                    thumb = ImageOps.exif_transpose(source).convert("RGB")
                thumb.thumbnail((180, 180))
            except Exception:
                continue
            image = ctk.CTkImage(light_image=thumb, dark_image=thumb, size=thumb.size)
            self.preview_refs.append(image)
            card = ctk.CTkFrame(self.results_frame, corner_radius=12, fg_color=("#F7F7F8", "#1A1A1E"))
            card.grid(row=start_row + 1 + index // cols, column=index % cols, padx=6, pady=6, sticky="nsew")
            ctk.CTkLabel(card, image=image, text="").pack(padx=8, pady=(8, 4))
            name = path.name if len(path.name) <= 19 else path.name[:18] + "…"
            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=10), text_color=SECONDARY_TEXT).pack(padx=8, pady=(0, 8))
            if index % 6 == 5:
                self.update_idletasks()
        if len(self.image_paths) > cap:
            ctk.CTkLabel(self.results_frame, text=f"+ {len(self.image_paths) - cap}장 더", font=ctk.CTkFont(size=12), text_color=MUTED_TEXT).grid(row=start_row + 2 + (len(shown) - 1) // cols, column=0, columnspan=3, pady=10)

    def _compose_settings_preview(self, style: str, strength: int, padding: int) -> Image.Image | None:
        if self._sample_face is None:
            return None
        processed = self._sample_face.copy()
        x1, y1, x2, y2 = SAMPLE_FACE_BOX
        width, height = x2 - x1, y2 - y1
        x1 = max(0, x1 - int(width * padding / 100))
        y1 = max(0, y1 - int(height * padding / 100))
        x2 = min(processed.width, x2 + int(width * padding / 100))
        y2 = min(processed.height, y2 + int(height * padding / 100))
        region = processed.crop((x1, y1, x2, y2))
        processed.paste(self._apply_effect(region, style, strength), (x1, y1))

        target_h = 200
        scaled = lambda im: im.resize((max(1, round(im.width * target_h / im.height)), target_h), Image.Resampling.LANCZOS)
        left, right = scaled(self._sample_face), scaled(processed)
        gap = 20
        canvas = Image.new("RGBA", (left.width + gap + right.width, target_h), (0, 0, 0, 0))
        canvas.paste(left.convert("RGBA"), (0, 0))
        canvas.paste(right.convert("RGBA"), (left.width + gap, 0))
        return canvas

    def _refresh_settings_card(self) -> None:
        if self._results_mode != "preview":
            return
        label = getattr(self, "settings_card_label", None)
        if label is None or not label.winfo_exists():
            return
        style, strength, padding = self.style_var.get(), int(self.strength_var.get()), int(self.padding_var.get())
        composite = self._compose_settings_preview(style, strength, padding)
        if composite is None:
            label.configure(text="샘플 이미지를 불러오지 못했습니다.")
            return
        image = ctk.CTkImage(light_image=composite, dark_image=composite, size=composite.size)
        self._settings_preview_ref = image
        label.configure(image=image, text="")
        self.settings_caption.configure(text=f"왼쪽 원본  →  오른쪽처럼 ‘{style}’ 적용  (강도 {strength} · 여백 {padding}%)")

    def _on_setting_changed(self, *_) -> None:
        if self._results_mode != "preview":
            return
        if self._preview_after is not None:
            try:
                self.after_cancel(self._preview_after)
            except Exception:
                pass
        self._preview_after = self.after(60, self._refresh_settings_card)

    def select_images(self) -> None:
        paths = filedialog.askopenfilenames(title="처리할 사진 선택", filetypes=IMAGE_TYPES)
        if not paths:
            return
        existing = set(self.image_paths)
        self.image_paths.extend(Path(path) for path in paths if Path(path) not in existing)
        self.file_count.configure(text=f"사진 {len(self.image_paths)}장 선택됨", text_color=ACCENT, font=ctk.CTkFont(size=12, weight="bold"))
        self._set_status("준비 완료 — ‘모든 얼굴 가리기’를 눌러 시작하세요.", "busy")
        self.process_button.configure(state="normal")
        self._enter_preview_mode()

    def start_processing(self) -> None:
        if self.processing or not self.image_paths:
            return
        if FaceAnalysis is None:
            messagebox.showerror("라이브러리 필요", "InsightFace가 설치되지 않았습니다. requirements.txt를 설치한 뒤 다시 실행해주세요.")
            return
        self.processing = True
        self._results_mode = "results"
        self._append_log(f"처리 시작: 사진 {len(self.image_paths)}장 / 효과 {self.style_var.get()}")
        self.results = []
        self.preview_refs = []
        self._clear_results()
        self._reset_results_columns(1)
        self.process_button.configure(state="disabled", text="모델 준비 중...")
        self.save_button.configure(state="disabled")
        self._set_status("고정밀 얼굴 검출 모델을 불러오는 중입니다. 처음에는 다운로드가 필요할 수 있어요.", "busy")
        self._show_progress()
        settings = (self.style_var.get(), int(self.strength_var.get()), int(self.padding_var.get()), float(self.threshold_var.get()))
        people_snapshot = json.loads(json.dumps(self.exempt_people))
        self.exemption_button.configure(state="disabled")
        threading.Thread(target=self._process_worker, args=(list(self.image_paths), settings, people_snapshot), daemon=True).start()
        self.after(100, self._read_worker_messages)

    def _process_worker(self, paths: list[Path], settings: tuple[str, int, int, float], exempt_people: list[dict]) -> None:
        try:
            analyzer = self._make_analyzer(settings[3])
            for index, path in enumerate(paths, start=1):
                self.worker_messages.put(("progress", (index, len(paths), path.name)))
                result, detected, masked, exempted = self._anonymize(path, analyzer, *settings[:3], exempt_people)
                self.worker_messages.put(("result", ProcessedImage(path, result, detected, masked, exempted)))
            self.worker_messages.put(("done", None))
        except Exception as error:
            self.worker_messages.put(("error", f"{error}\n\n{traceback.format_exc()}"))

    @staticmethod
    def _is_exempt(embedding: np.ndarray, exempt_people: list[dict]) -> bool:
        if not exempt_people:
            return False
        for person in exempt_people:
            samples = np.asarray(person["embeddings"], dtype=np.float32)
            if samples.size and float(np.max(samples @ embedding)) >= EXEMPTION_MATCH_THRESHOLD:
                return True
        return False

    @classmethod
    def _anonymize(cls, path: Path, detector, style: str, strength: int, padding: int, exempt_people: list[dict]) -> tuple[Image.Image, int, int, int]:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        rgb = np.asarray(image)
        faces = detector.get(rgb)
        output = image.copy()
        masked_count = 0
        exempted_count = 0
        for face in faces:
            if cls._is_exempt(face.normed_embedding, exempt_people):
                exempted_count += 1
                continue
            x1, y1, x2, y2 = face.bbox.astype(int).tolist()
            width, height = x2 - x1, y2 - y1
            x1 = max(0, x1 - int(width * padding / 100))
            y1 = max(0, y1 - int(height * padding / 100))
            x2 = min(output.width, x2 + int(width * padding / 100))
            y2 = min(output.height, y2 + int(height * padding / 100))
            region = output.crop((x1, y1, x2, y2))
            output.paste(cls._apply_effect(region, style, strength), (x1, y1))
            masked_count += 1
        return output, len(faces), masked_count, exempted_count

    def _read_worker_messages(self) -> None:
        pending = False
        while not self.worker_messages.empty():
            kind, data = self.worker_messages.get()
            if kind == "progress":
                current, total, filename = data
                self.process_button.configure(text=f"처리 중 {current}/{total}")
                self._set_status(f"[{current}/{total}] {filename} 에서 얼굴을 찾는 중…", "busy")
                self._set_progress_fraction(current - 1, total)
                self._append_log(f"분석 중 ({current}/{total}): {filename}")
            elif kind == "result":
                self.results.append(data)
                self._add_preview(data)
            elif kind == "done":
                self.processing = False
                self._hide_progress()
                self.process_button.configure(state="normal", text="다시 처리하기")
                self.exemption_button.configure(state="normal")
                self._update_exemption_button()
                self.save_button.configure(state="normal")
                total_faces = sum(item.face_count for item in self.results)
                masked = sum(item.masked_count for item in self.results)
                exempted = sum(item.exempted_count for item in self.results)
                self._set_status(f"완료 — 사진 {len(self.results)}장 · 얼굴 {total_faces}개 감지 · {masked}개 가림 · 예외 {exempted}개", "done")
                self._append_log(f"완료: 얼굴 {total_faces}개 감지, {masked}개 가림, 예외 {exempted}개 제외")
            elif kind == "save_progress":
                current, total = data
                self._set_progress_fraction(current, total)
                self.save_button.configure(text=f"저장 중 {current}/{total}")
            elif kind == "save_done":
                folder, count = data
                self.processing = False
                self._hide_progress()
                self.save_button.configure(state="normal", text="결과 전체 저장")
                self.process_button.configure(state="normal")
                self.exemption_button.configure(state="normal")
                self._set_status(f"저장 완료 — {count}장을 저장했습니다. 저장 폴더를 열었어요.", "done")
                self._append_log(f"결과 저장 완료: {count}장 → {folder}")
                try:
                    os.startfile(folder)  # open the destination folder in Explorer
                except Exception:
                    self._append_log("저장 폴더를 자동으로 열지 못했습니다.")
            elif kind == "save_error":
                self.processing = False
                self._hide_progress()
                self.save_button.configure(state="normal", text="결과 전체 저장")
                self.process_button.configure(state="normal")
                self.exemption_button.configure(state="normal")
                self._set_status("저장 중 오류가 발생했습니다.", "warn")
                self._append_log(f"저장 오류: {data}")
                messagebox.showerror("저장 오류", str(data))
            elif kind == "registration_candidates":
                self._hide_progress()
                self._set_status("등록할 얼굴을 선택해 주세요.", "busy")
                self._append_log(f"예외 인물 후보 {len(data['candidates'])}개 감지 — 사용자 라벨링 대기")
                self._open_face_label_dialog(data["name"], data["candidates"], data["skipped"], data.get("person_index"))
            elif kind == "registration_error":
                self.processing = False
                self._hide_progress()
                self.exemption_button.configure(state="normal")
                self._update_exemption_button()
                self.process_button.configure(state="normal" if self.image_paths else "disabled")
                self._set_status("예외 인물 등록 중 오류가 발생했습니다.", "warn")
                self._append_log(f"예외 인물 등록 오류:\n{data}")
                if not self.log_visible:
                    self._toggle_log()
                messagebox.showerror("등록 오류", f"{str(data).split(chr(10))[0]}\n\n아래 오류 로그에서 전체 내용을 확인하세요.")
            elif kind == "error":
                self.processing = False
                self._hide_progress()
                self.process_button.configure(state="normal", text="다시 시도하기")
                self.exemption_button.configure(state="normal")
                self._update_exemption_button()
                self._set_status("처리 중 오류가 발생했습니다.", "warn")
                self._append_log(f"오류 발생:\n{data}")
                if not self.log_visible:
                    self._toggle_log()
                messagebox.showerror("처리 오류", f"{str(data).split(chr(10))[0]}\n\n아래의 오류 로그에서 전체 내용을 확인할 수 있습니다.")
        if self.processing:
            self.after(100, self._read_worker_messages)

    def _clear_results(self) -> None:
        for widget in self.results_frame.winfo_children():
            widget.destroy()

    def _add_preview(self, result: ProcessedImage) -> None:
        if len(self.results) == 1:
            self._clear_results()
        elif len(self.results) == 2:
            self.results_frame._scrollbar.grid()
        thumbnail = result.image.copy()
        thumbnail.thumbnail((680, 440))
        display = ctk.CTkImage(light_image=thumbnail, dark_image=thumbnail, size=thumbnail.size)
        self.preview_refs.append(display)
        card = ctk.CTkFrame(self.results_frame, corner_radius=16, fg_color=("#F7F7F8", "#1A1A1E"))
        card.grid(row=len(self.results)-1, column=0, columnspan=3, pady=(0, 14), padx=4, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, image=display, text="").grid(row=0, column=0, padx=18, pady=(18, 10))
        ctk.CTkLabel(card, text=result.source.name, font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, padx=18, sticky="w")
        info = f"감지 {result.face_count}개 · 모자이크 {result.masked_count}개"
        if result.exempted_count:
            info += f" · 예외 {result.exempted_count}개"
        ctk.CTkLabel(card, text=info, font=ctk.CTkFont(size=11), text_color=ACCENT).grid(row=2, column=0, padx=18, pady=(2, 16), sticky="w")

    def save_results(self) -> None:
        if not self.results or self.processing:
            return
        destination = filedialog.askdirectory(title="결과를 저장할 폴더 선택")
        if not destination:
            return
        # Saving runs on a worker thread so the window never shows "응답 없음".
        self.processing = True
        self.save_button.configure(state="disabled", text="저장 중...")
        self.process_button.configure(state="disabled")
        self.exemption_button.configure(state="disabled")
        self._set_status(f"결과 {len(self.results)}장을 저장하는 중입니다…", "busy")
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.progress_bar.grid()
        self._append_log(f"결과 저장 시작: {len(self.results)}장 → {destination}")
        threading.Thread(target=self._save_worker, args=(list(self.results), Path(destination)), daemon=True).start()
        self.after(100, self._read_worker_messages)

    def _save_worker(self, results: list[ProcessedImage], folder: Path) -> None:
        try:
            for index, result in enumerate(results, start=1):
                # PNG avoids any additional JPEG compression after face masking.
                result.image.save(folder / f"{result.source.stem}_mosaic.png", "PNG", optimize=True)
                self.worker_messages.put(("save_progress", (index, len(results))))
            self.worker_messages.put(("save_done", (str(folder), len(results))))
        except OSError as error:
            self.worker_messages.put(("save_error", str(error)))


if __name__ == "__main__":
    OnlyMyFaceApp().mainloop()
