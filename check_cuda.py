import subprocess
import sys

print("=" * 50)
print("  CUDA / cuDNN 환경 확인 스크립트")
print("=" * 50)

# 1. nvidia-smi
print("\n[1] nvidia-smi (GPU 드라이버 확인)")
try:
    result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    if result.returncode == 0:
        # 간략하게 첫 10줄만 출력
        lines = result.stdout.strip().split("\n")
        for line in lines[:10]:
            print(line)
    else:
        print("❌ nvidia-smi 실패 - NVIDIA 드라이버가 설치되지 않았거나 GPU가 없습니다.")
except FileNotFoundError:
    print("❌ nvidia-smi를 찾을 수 없습니다. NVIDIA 드라이버를 설치해 주세요.")

# 2. PyTorch CUDA 확인
print("\n[2] PyTorch CUDA 확인")
try:
    import torch
    print(f"  PyTorch 버전  : {torch.__version__}")
    print(f"  CUDA 사용가능  : {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  CUDA 버전     : {torch.version.cuda}")
        print(f"  cuDNN 버전    : {torch.backends.cudnn.version()}")
        print(f"  GPU 개수      : {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"  GPU {i}         : {torch.cuda.get_device_name(i)}")

        # 3. 실제 GPU 연산 테스트
        print("\n[3] GPU 연산 테스트 (Tensor 연산)")
        a = torch.randn(1000, 1000).cuda()
        b = torch.randn(1000, 1000).cuda()
        c = torch.mm(a, b)
        print(f"  1000x1000 행렬 곱셈 성공! 결과 shape: {c.shape}")
        print(f"  결과 device: {c.device}")

        # 4. cuDNN 테스트
        print("\n[4] cuDNN 테스트 (CNN 연산)")
        import torch.nn as nn
        conv = nn.Conv2d(3, 64, kernel_size=3, padding=1).cuda()
        x = torch.randn(1, 3, 224, 224).cuda()
        y = conv(x)
        print(f"  Conv2d 연산 성공! 출력 shape: {y.shape}")

        print("\n✅ 모든 테스트 통과! CUDA와 cuDNN이 정상적으로 동작합니다.")
    else:
        print("  ❌ CUDA를 사용할 수 없습니다.")
        print("  → PyTorch가 CPU 버전으로 설치됐을 수 있습니다.")
        print("  → https://pytorch.org 에서 CUDA 버전으로 재설치해 주세요.")

except ImportError:
    print("  ❌ PyTorch가 설치되지 않았습니다.")
    print("  → pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")

print("\n" + "=" * 50)
