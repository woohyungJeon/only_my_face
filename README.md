# Only My Face

사진 속 **모든 얼굴**을 PC에서 감지해 모자이크 또는 블러 처리하는 개인용 데스크톱 앱입니다. 사진은 외부 서버로 전송되지 않습니다.

## 실행

가장 간단한 방법은 프로젝트 폴더의 `OnlyMyFace 실행.vbs`를 더블클릭하는 것입니다. 검은 터미널 창 없이 앱이 열립니다.

터미널에서 실행하려면:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 app.py
```

첫 처리 때 InsightFace `buffalo_l` 얼굴 검출 모델이 자동으로 다운로드됩니다. 네트워크와 저장 공간 약 326MB가 필요하며, 이후에는 로컬에서 실행됩니다.

## 사용법

1. **파일 선택**으로 사진을 여러 장 선택합니다.
2. 효과(모자이크/블러), 강도, 얼굴 주변 여백, 검출 민감도를 정합니다.
3. **모든 얼굴 가리기**를 누르고 결과를 확인합니다.
4. **결과 전체 저장**으로 원본명 뒤에 `_mosaic.jpg`가 붙은 파일을 저장합니다.

`buffalo_l` 사전학습 모델은 비상업 연구·개인 프로젝트 용도로 사용합니다. 상업적 배포나 서비스 전환 전에는 InsightFace 모델 라이선스를 별도로 검토해야 합니다.

## 일반 사용자용 Windows 설치 파일 만들기

일반 사용자는 Python이나 명령어를 설치할 필요가 없습니다. `OnlyMyFace-Setup.exe` 하나를 실행하면 바탕화면에 **Only My Face** 아이콘이 생성됩니다.

설치본에는 다음을 모두 포함합니다.

- 64비트 Python 3.12 실행 환경과 필수 DLL
- 얼굴 인식 라이브러리와 CPU용 ONNX Runtime
- InsightFace `buffalo_l` 모델 (약 326MB)
- Pretendard 글꼴과 앱 아이콘

따라서 설치 후에는 인터넷 없이 실행할 수 있습니다. 설치본 용량은 모델과 실행 환경 때문에 수백 MB 수준입니다. 설정, 예외 인물, 로그는 `%LOCALAPPDATA%\OnlyMyFace`에 저장되므로 업데이트와 제거 과정에서도 유지됩니다.

### 빌드하는 사람만 하는 작업

1. Python 3.12에서 앱을 한 번 실행해 `buffalo_l` 모델을 내려받습니다.
2. [Inno Setup 6](https://jrsoftware.org/isinfo.php)을 설치합니다.
3. 프로젝트 폴더에서 다음을 실행합니다.

```powershell
.\build_release.ps1
```

성공하면 `dist\OnlyMyFace-Setup.exe`가 만들어집니다. 이전 `build_exe.ps1`의 PyInstaller 단일 exe 방식은 ONNX Runtime DLL 초기화 문제 때문에 배포용으로 사용하지 않습니다.
