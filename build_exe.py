import PyInstaller.__main__
import os

# EXE'yi oluştur
PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--windowed',
    '--name=TCKimlikIslemci',
    '--icon=app.ico',  # Kendi ikon dosyanızı ekleyin
    '--add-data=assets;assets',  # Gerekli asset klasörü
    '--distpath=./dist',
    '--workpath=./build',
    '--clean'
])