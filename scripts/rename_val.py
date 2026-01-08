import shutil
import os

src = os.path.join("rawdoc", "从业考试验证集.xlsx")
dst = os.path.join("rawdoc", "validation_set.xlsx")

if os.path.exists(src):
    shutil.copy(src, dst)
    print(f"Copied {src} to {dst}")
else:
    print(f"Source file not found: {src}")



