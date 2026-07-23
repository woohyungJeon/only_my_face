# Only My Face

사진 속 **모든 얼굴**을 PC에서 감지해 모자이크 또는 블러 처리하는 개인용 데스크톱 앱입니다. 사진은 외부 서버로 전송되지 않습니다.

## 실행

가장 간단한 방법은 프로젝트 폴더의 `OnlyMyFace 실행.vbs`를 더블클릭하는 것입니다. 검은 터미널 창 없이 앱이 열립니다.

터미널에서 실행하려면:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 app.py
```

얼굴 검출과 예외 인물 비교에 필요한 YuNet, MP-PersonDet 및 SFace 모델은 앱에 포함되어 있습니다. 첫 실행 시 모델 다운로드가 필요하지 않습니다.

## 사용법

1. **파일 선택**으로 사진을 여러 장 선택합니다.
2. 효과(모자이크/블러), 강도, 얼굴 주변 여백, 검출 민감도를 정합니다.
3. **모든 얼굴 가리기**를 누르고 결과를 확인합니다.
4. **결과 전체 저장**으로 원본명 뒤에 `_mosaic.jpg`가 붙은 파일을 저장합니다.

YuNet(MIT), MP-PersonDet(Apache-2.0) 및 SFace(Apache-2.0) 모델의 라이선스 고지는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 및 `assets/models` 폴더에 포함되어 있습니다.

## 일반 사용자용 Windows 설치 파일 만들기

일반 사용자는 Python이나 명령어를 설치할 필요가 없습니다. `OnlyMyFace-Setup.exe` 하나를 실행하면 바탕화면에 **Only My Face** 아이콘이 생성됩니다.

설치본에는 다음을 모두 포함합니다.

- 64비트 Python 3.12 실행 환경과 필수 DLL
- OpenCV 실행 환경
- YuNet 얼굴 검출 모델, MP-PersonDet 옆·뒷모습 안전망, SFace 예외 인물 비교 모델
- Pretendard 글꼴과 앱 아이콘

따라서 설치 후에는 인터넷 없이 실행할 수 있습니다. 설치본 용량은 모델과 실행 환경 때문에 수백 MB 수준입니다. 설정, 예외 인물, 로그는 `%LOCALAPPDATA%\OnlyMyFace`에 저장되므로 업데이트와 제거 과정에서도 유지됩니다.

### 빌드하는 사람만 하는 작업

1. [Inno Setup 6](https://jrsoftware.org/isinfo.php)을 설치합니다.
2. 프로젝트 폴더에서 다음을 실행합니다.

```powershell
.\build_release.ps1
```

성공하면 `dist\OnlyMyFace-Setup.exe`가 만들어집니다. 이전 `build_exe.ps1`의 PyInstaller 단일 exe 방식은 ONNX Runtime DLL 초기화 문제 때문에 배포용으로 사용하지 않습니다.
