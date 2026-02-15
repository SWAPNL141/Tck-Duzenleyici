import PyInstaller.__main__
import os

# EXE'yi oluştur
PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--windowed',
    '--name=TCKimlikIslemci',
    '--icon=app.ico',
    '--add-data=assets;assets',
    '--hidden-import=cv2',
    '--hidden-import=numpy',
    '--hidden-import=PIL',
    '--hidden-import=PIL.Image',
    '--hidden-import=PIL.ImageTk',
    '--hidden-import=PIL.ImageOps',
    '--collect-all=cv2',
    '--collect-all=numpy',
    '--collect-all=PIL',
    '--distpath=./dist',
    '--workpath=./build',
    '--clean'
])
