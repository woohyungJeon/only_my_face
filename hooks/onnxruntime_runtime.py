"""Make ONNX Runtime's native DLL directory visible in a PyInstaller app."""

import os
import sys

if getattr(sys, "frozen", False):
    capi_dir = os.path.join(sys._MEIPASS, "onnxruntime", "capi")
    if os.path.isdir(capi_dir):
        os.add_dll_directory(capi_dir)
