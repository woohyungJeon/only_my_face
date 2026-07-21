# Deprecated: PyInstaller cannot reliably package ONNX Runtime in this app.
# Keep this friendly entry point so an old build command does not claim success
# after producing a broken exe.
Write-Host "PyInstaller 단일 exe 방식은 ONNX Runtime DLL 오류 때문에 사용하지 않습니다." -ForegroundColor Yellow
Write-Host "일반 사용자용 설치 파일은 다음 명령으로 만드세요:" -ForegroundColor Cyan
Write-Host "  .\build_release.ps1"
Write-Host "(처음 한 번만 Inno Setup 6 설치가 필요합니다: https://jrsoftware.org/isinfo.php)"
exit 1
