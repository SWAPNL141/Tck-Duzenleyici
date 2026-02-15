# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps
import PIL.PdfImagePlugin  # PyInstaller icin PDF eklentisini acikca yukle
import threading
import sys
import subprocess
import platform
from datetime import datetime
import shutil

def imread_unicode(path):
    """Turkce karakterli dosya yollarini destekleyen goruntu okuma"""
    try:
        # Oncelikle cv2 ile dene
        img = cv2.imread(path)
        if img is not None:
            return img
    except Exception:
        pass
    # cv2 basarisisz ise numpy + PIL ile oku
    try:
        pil_img = Image.open(path)
        if pil_img.mode == 'RGBA':
            pil_img = pil_img.convert('RGB')
        img_array = np.array(pil_img)
        # PIL RGB, OpenCV BGR - kanal siralamasi duzelt
        if len(img_array.shape) == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        return img_array
    except Exception as e:
        print(f"Goruntu okunamadi: {path} - {e}")
        return None

def imwrite_unicode(path, img):
    """Turkce karakterli dosya yollarini destekleyen goruntu kaydetme"""
    try:
        # Oncelikle cv2 ile dene
        success = cv2.imwrite(path, img)
        if success:
            return True
    except Exception:
        pass
    # cv2 basarisiz ise PIL ile kaydet
    try:
        if len(img.shape) == 2:
            pil_img = Image.fromarray(img, mode='L')
        else:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
        pil_img.save(path)
        return True
    except Exception as e:
        print(f"Goruntu kaydedilemedi: {path} - {e}")
        return False


class IDCardProcessor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TC Kimlik Kartı Düzenleyici v1 by SWAPNIL")
        self.root.geometry("1000x750") # Başlangıç boyutu
        self.root.resizable(False, False) # Pencere boyutunu kilitle

        # Görev çubuğu ve başlık ikonunu ayarla
        # PyInstaller ile paketlenmiş olup olmadığını kontrol et
        if getattr(sys, 'frozen', False):
            # PyInstaller ile paketlenmişse, geçici dizini kullan
            base_path = sys._MEIPASS
        else:
            # Normal Python betiği olarak çalışıyorsa, mevcut dizini kullan
            base_path = os.path.abspath(".")

        icon_loaded = False
        # Önce .png ikonunu dene (daha esnek ve çapraz platform uyumlu)
        png_icon_name = 'app_icon.png' # PNG ikon dosyanızın adı
        png_icon_path = os.path.join(base_path, png_icon_name)
        try:
            if os.path.exists(png_icon_path):
                img = Image.open(png_icon_path)
                # İkon boyutunu ayarlayın (örneğin 64x64 veya 128x128)
                # İkonlar genellikle küçük boyutlarda daha iyi görünür.
                img = img.resize((64, 64), Image.LANCZOS) 
                photo = ImageTk.PhotoImage(img)
                # iconphoto(True, photo) tüm üst düzey pencereler için ikonu ayarlar
                self.root.iconphoto(True, photo) 
                icon_loaded = True
                print(f"Bilgi: '{png_icon_name}' ikonu başarıyla yüklendi.")
            else:
                print(f"Uyarı: '{png_icon_name}' dosyası bulunamadı.")
        except Exception as e:
            print(f"Hata: PNG ikon yüklenirken bir sorun oluştu: {e}.")

        # Eğer PNG ikonu yüklenemezse, .ico ikonunu dene (Windows için)
        if not icon_loaded:
            ico_icon_name = 'app.ico' # ICO ikon dosyanızın adı
            ico_icon_path = os.path.join(base_path, ico_icon_name)
            try:
                if os.path.exists(ico_icon_path):
                    self.root.iconbitmap(ico_icon_path) 
                    icon_loaded = True
                    print(f"Bilgi: '{ico_icon_name}' ikonu başarıyla yüklendi.")
                else:
                    print(f"Uyarı: '{ico_icon_name}' dosyası bulunamadı.")
            except tk.TclError as e:
                print(f"Hata: ICO ikon yüklenirken bir sorun oluştu: {e}.")
        
        if not icon_loaded:
            print("Uyarı: Hiçbir özel ikon yüklenemedi. Varsayılan ikon kullanılacak.")


        # Değişkenleri başlat
        self.temp_dir = os.path.join(os.getenv("TEMP"), "kimlik_islemleri")
        self.front_image_path = ""
        self.back_image_path = ""
        self.last_pdf_path = ""
        
        # Belgeler klasörüne sabit kayıt yolu
        documents_path = os.path.join(os.path.expanduser("~"), "Documents")
        self.output_dir = os.path.join(documents_path, "TC_Kimlik_Islemleri")
        
        # Klasörleri oluştur
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # UI'yı kur
        self.setup_ui()
        
        # Stil ayarları
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Helvetica', 10), padding=5)
        self.style.configure('TLabel', font=('Helvetica', 9))
        self.style.configure('Title.TLabel', font=('Helvetica', 12, 'bold'))

    def setup_ui(self):
        # Ana çerçeve - root'u dolduracak ve grid layout kullanacak
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew") # main_frame, root penceresini doldurur
        self.root.grid_rowconfigure(0, weight=1) # root'un 0. satırının genişlemesine izin ver
        self.root.grid_columnconfigure(0, weight=1) # root'un 0. sütununun genişlemesine izin ver

        # main_frame içindeki satırların konfigürasyonu
        # Row 0: control_frame (sabit yükseklik)
        # Row 1: info_frame (sabit yükseklik)
        # Row 2: settings_frame (sabit yükseklik)
        # Row 3: img_display_frame (dikey olarak genişler)
        # Row 4: bottom_frame (sabit yükseklik)
        main_frame.grid_rowconfigure(3, weight=1) # img_display_frame'in bulunduğu satır genişleyecek
        main_frame.grid_columnconfigure(0, weight=1) # main_frame'in tek sütunu genişleyecek

        # Kontrol paneli
        control_frame = ttk.LabelFrame(main_frame, text="Dosya Seçimleri", padding="10")
        control_frame.grid(row=0, column=0, sticky="ew", pady=5) # Grid layout kullan
        control_frame.grid_columnconfigure(1, weight=1) # Dosya yolu etiketinin genişlemesine izin ver

        ttk.Button(control_frame, text="Ön Yüz Seç", 
                   command=lambda: self.select_image("front")).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.front_label = ttk.Label(control_frame, text="Seçili dosya: Yok")
        self.front_label.grid(row=0, column=1, padx=5, sticky='ew') # Yatayda genişle

        ttk.Button(control_frame, text="Arka Yüz Seç", 
                   command=lambda: self.select_image("back")).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.back_label = ttk.Label(control_frame, text="Seçili dosya: Yok")
        self.back_label.grid(row=1, column=1, padx=5, sticky='ew') # Yatayda genişle
        
        # Kayıt yolu bilgisi
        info_frame = ttk.LabelFrame(main_frame, text="Kayıt Bilgisi", padding="10")
        info_frame.grid(row=1, column=0, sticky="ew", pady=5) # Grid layout kullan
        ttk.Label(info_frame, text="Dosyalar şuraya kaydedilecek:", font=('Helvetica', 9, 'bold')).pack(anchor='w')
        ttk.Label(info_frame, text=self.output_dir, foreground='blue').pack(anchor='w', padx=20)

        # İşlem ayarları
        settings_frame = ttk.LabelFrame(main_frame, text="İşlem Ayarları", padding="10")
        settings_frame.grid(row=2, column=0, sticky="ew", pady=5) # Grid layout kullan
        settings_frame.grid_columnconfigure(1, weight=1) # Scale sütununun genişlemesine izin ver
        
        self.auto_crop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Akıllı TC Kimlik Kırpma (Boy/En oranı korunur)", 
                        variable=self.auto_crop_var).grid(row=0, column=0, sticky='w', padx=5, columnspan=3)
        
        ttk.Label(settings_frame, text="Kenar Boşluğu:").grid(row=1, column=0, padx=5, sticky='w')
        self.margin_var = tk.IntVar(value=10) # Varsayılan kenar boşluğunu 10px'e geri çektim
        margin_scale = ttk.Scale(settings_frame, from_=0, to=50, variable=self.margin_var, orient=tk.HORIZONTAL)
        margin_scale.grid(row=1, column=1, padx=5, sticky='ew') # Yatayda genişle
        self.margin_label = ttk.Label(settings_frame, text="10px") # Etiket değerini de güncelle
        self.margin_label.grid(row=1, column=2, padx=5)
        margin_scale.configure(command=self.update_margin_label)
        
        ttk.Label(settings_frame, text="Min. Kart Boyutu:").grid(row=2, column=0, padx=5, sticky='w')
        self.min_size_var = tk.IntVar(value=15)
        size_scale = ttk.Scale(settings_frame, from_=5, to=50, variable=self.min_size_var, orient=tk.HORIZONTAL)
        size_scale.grid(row=2, column=1, padx=5, sticky='ew')
        self.size_label = ttk.Label(settings_frame, text="%15")
        self.size_label.grid(row=2, column=2, padx=5)
        size_scale.configure(command=self.update_size_label)
        
        ttk.Label(settings_frame, text="İyileştirme Seviyesi:").grid(row=3, column=0, padx=5, sticky='w')
        self.quality_var = tk.IntVar(value=70)
        quality_scale = ttk.Scale(settings_frame, from_=10, to=100, variable=self.quality_var, orient=tk.HORIZONTAL)
        quality_scale.grid(row=3, column=1, padx=5, sticky='ew') # Yatayda genişle
        self.quality_label = ttk.Label(settings_frame, text="70%")
        self.quality_label.grid(row=3, column=2, padx=5)
        quality_scale.configure(command=self.update_quality_label)

        # Görüntü görüntüleme alanı
        img_display_frame = ttk.LabelFrame(main_frame, text="Görüntü Önizleme", padding="10")
        img_display_frame.grid(row=3, column=0, sticky="nsew", pady=5) # Grid layout kullan, genişlemesine izin ver
        img_display_frame.grid_columnconfigure(0, weight=1) # Önizleme etiketi sütununun genişlemesine izin ver
        img_display_frame.grid_columnconfigure(1, weight=1) # Arka yüz etiketi sütununun genişlemesine izin ver
        img_display_frame.grid_rowconfigure(0, weight=1) # Etiketlerin dikey olarak genişlemesine izin ver

        # Ön ve arka yüz görüntüleri için sabit boyutlu çerçeveler
        # Bu çerçeveler, içlerindeki Label'ın boyutunu kontrol eder.
        # Önizleme çerçevesinin boyutunu daha dinamik hale getirdim.
        self.front_view_frame = ttk.Frame(img_display_frame) 
        self.front_view_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.front_view_frame.grid_propagate(False) # Çerçevenin içeriğine göre küçülmesini engelle

        self.front_view = ttk.Label(self.front_view_frame, text="Ön Yüz Seçilmedi\n(Lütfen yukarıdan dosya seçin)", 
                                     justify=tk.CENTER, style='Title.TLabel')
        self.front_view.pack(fill=tk.BOTH, expand=True) # Etiketi çerçevesini dolduracak şekilde pack et

        self.back_view_frame = ttk.Frame(img_display_frame) 
        self.back_view_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.back_view_frame.grid_propagate(False) # Çerçevenin içeriğine göre küçülmesini engelle

        self.back_view = ttk.Label(self.back_view_frame, text="Arka Yüz Seçilmedi\n(Lütfen yukarıdan dosya seçin)", 
                                    justify=tk.CENTER, style='Title.TLabel')
        self.back_view.pack(fill=tk.BOTH, expand=True) # Etiketi çerçevesini dolduracak şekilde pack et

        # İlerleme çubuğu ve butonlar
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=4, column=0, sticky="ew", pady=10) # Grid layout kullan
        bottom_frame.grid_columnconfigure(0, weight=1) # İlerleme çubuğu sütununun genişlemesine izin ver
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5) # İki sütuna yayıl
        
        self.status_label = ttk.Label(bottom_frame, text="Hazır", anchor=tk.W)
        self.status_label.grid(row=1, column=0, sticky="ew")
        
        btn_frame = ttk.Frame(bottom_frame)
        btn_frame.grid(row=1, column=1, sticky="e") # Butonlari saga hizala
        
        ttk.Button(btn_frame, text="Yazdır", 
                   command=self.print_pdf).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Klasörü Aç", 
                   command=self.open_output_folder).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="İşlemi Başlat", 
                   command=self.start_processing).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Çıkış", 
                   command=self.cleanup_and_exit).pack(side=tk.RIGHT, padx=5)

    def update_margin_label(self, value):
        self.margin_label.config(text=f"{int(float(value))}px")
    
    def update_size_label(self, value):
        self.size_label.config(text=f"%{int(float(value))}")
    
    def update_quality_label(self, value):
        self.quality_label.config(text=f"{int(float(value))}%")

    def select_image(self, side):
        try:
            file_path = filedialog.askopenfilename(
                title=f"TC Kimlik {side.capitalize()} Yüzünü Seçin",
                filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp"), ("Tüm Dosyalar", "*.*")]
            )
            
            if not file_path:
                return
            
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.bmp'):
                raise ValueError("Desteklenmeyen dosya formatı. Lütfen JPG, PNG veya BMP seçin.")
            
            try:
                with Image.open(file_path) as img:
                    img.verify()
            except Exception as e:
                raise ValueError(f"Geçersiz resim dosyası: {str(e)}")
            
            # Gecici dosya adinda sadece ASCII kullan (Turkce karakter sorunu onlenir)
            safe_name = f"{side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            temp_path = os.path.join(self.temp_dir, safe_name)
            try:
                shutil.copy2(file_path, temp_path)
            except Exception:
                # shutil basarisiz olursa PIL ile oku/yaz
                pil_img = Image.open(file_path)
                pil_img.save(temp_path)
                pil_img.close()
            
            if side == "front":
                self.front_image_path = temp_path
                self.front_label.config(text=f"Seçili dosya: {os.path.basename(file_path)}")
                self.display_image(temp_path, self.front_view)
            else:
                self.back_image_path = temp_path
                self.back_label.config(text=f"Seçili dosya: {os.path.basename(file_path)}")
                self.display_image(temp_path, self.back_view)
                
            self.update_status(0, f"{side.capitalize()} yüz başarıyla yüklendi")
        except Exception as e:
            messagebox.showerror("Dosya Seçme Hatası", str(e))
            self.update_status(0, f"{side.capitalize()} yüz yüklenemedi")

    def display_image(self, image_path, label_widget):
        try:
            # Etiketin ana çerçevesinin mevcut boyutlarını al
            # Bu, çerçevenin layout tarafından boyutlandırılmasını bekler
            label_widget.master.update_idletasks() # Çerçevenin boyutlarının güncellendiğinden emin ol
            frame_width = label_widget.master.winfo_width()
            frame_height = label_widget.master.winfo_height()

            # Eğer henüz boyutlar alınamadıysa (ilk yüklemede olabilir) varsayılan bir değer kullan
            # Bu varsayılan değerler, uygulamanın başlangıçtaki görünümünü korumak için önemlidir.
            if frame_width < 100 or frame_height < 100: # Güvenli bir alt sınır
                frame_width = 450 
                frame_height = 450

            img = Image.open(image_path)
            
            # Resmi çerçevenin boyutlarına sığacak şekilde yeniden boyutlandır
            # Image.LANCZOS, daha iyi kalite için kullanılır
            img.thumbnail((frame_width, frame_height), Image.LANCZOS)
            
            # RGBA (şeffaf) görüntüleri RGB'ye dön��ştürerek arka plan sorunlarını önle
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (240, 240, 240)) # Gri tonlu arka plan
                background.paste(img, mask=img.split()[-1]) # Alfa kanalını maske olarak kullan
                img = background
            
            photo = ImageTk.PhotoImage(img)
            label_widget.config(image=photo)
            label_widget.image = photo # Çöp toplamasını önlemek için referansı tut
            label_widget.config(text="") # Yer tutucu metni temizle
        except Exception as e:
            label_widget.config(image=None, text=f"Görüntü gösterilemedi:\n{str(e)}")

    def detect_id_card_with_aspect_ratio(self, image):
        """TC Kimlik kartını boy/en oranıyla birlikte algıla"""
        try:
            original_height, original_width = image.shape[:2]
            print(f"Orijinal görüntü boyutu: {original_width}x{original_height}")
            
            # Görüntüyü gri tonlamalı yap
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Çoklu yöntem deneme
            methods = [
                self.method_canny_contours,
                self.method_adaptive_threshold,
                self.method_gradient_based
            ]
            
            for i, method in enumerate(methods):
                print(f"Yöntem {i+1} deneniyor...")
                result = method(gray, original_width, original_height)
                if result:
                    x, y, w, h = result
                    print(f"Yöntem {i+1} başarılı: {w}x{h} boyutunda kart bulundu")
                    return result
            
            print("Hiçbir yöntem başarılı olmadı")
            return None
            
        except Exception as e:
            print(f"Kimlik kartı algılama hatası: {str(e)}")
            return None

    def method_canny_contours(self, gray, orig_width, orig_height):
        """Canny kenar algılama + kontür yöntemi"""
        try:
            # Gürültüyü azalt
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Canny kenar algılama - farklı threshold değerleri dene
            for low_thresh in [30, 50, 70]:
                for high_thresh in [80, 120, 150]:
                    edges = cv2.Canny(blurred, low_thresh, high_thresh, apertureSize=3)
                    
                    # Morfolojik işlemler
                    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
                    
                    # Kontürleri bul
                    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    if contours:
                        result = self.analyze_contours(contours, orig_width, orig_height)
                        if result:
                            return result
            
            return None
        except: # Hata durumunda None döndür
            return None

    def method_adaptive_threshold(self, gray, orig_width, orig_height):
        """Adaptive threshold yöntemi"""
        try:
            # Adaptive threshold
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY_INV, 11, 2)
            
            # Morfolojik işlemler
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
            
            # Kontürleri bul
            contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                return self.analyze_contours(contours, orig_width, orig_height)
            
            return None
        except: # Hata durumunda None döndür
            return None

    def method_gradient_based(self, gray, orig_width, orig_height):
        """Gradient tabanlı yöntem"""
        try:
            # Sobel gradientleri
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            # Gradient büyüklüğü
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            magnitude = np.uint8(magnitude / magnitude.max() * 255)
            
            # Threshold
            _, thresh = cv2.threshold(magnitude, 50, 255, cv2.THRESH_BINARY)
            
            # Morfolojik işlemler
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
            morphed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
            
            # Kontürleri bul
            contours, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                return self.analyze_contours(contours, orig_width, orig_height)
            
            return None
        except: # Hata durumunda None döndür
            return None

    def _is_id_card_ratio(self, aspect_ratio):
        """TC kimlik kartı oranını kontrol et (yatay veya dikey)"""
        # TC kimlik: 85.6mm x 53.98mm ≈ 1.586
        # Yatay (landscape): 1.2 - 2.0
        # Dikey (portrait):  0.5 - 0.83 (1/2.0 - 1/1.2)
        return (1.2 < aspect_ratio < 2.0) or (0.5 < aspect_ratio < 0.83)

    def analyze_contours(self, contours, orig_width, orig_height):
        """Kontürleri analiz et ve en uygun kimlik kartını bul"""
        try:
            # Kontürleri alan büyüklüğüne göre sırala
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            min_area_pct = self.min_size_var.get()  # 5-50 arasi tam sayi
            min_area_ratio = min_area_pct / 100.0
            min_area = (orig_width * orig_height) * min_area_ratio
            
            print(f"Minimum alan: {min_area:.0f} (goruntunun %{min_area_pct}'i)")
            
            best_candidate = None
            best_score = 0
            
            # En büyük 15 kontürü kontrol et
            for i, contour in enumerate(contours[:15]):
                area = cv2.contourArea(contour)
                
                if area < min_area:
                    print(f"Kontür {i+1} ({area:.0f} alan): Alan çok küçük, atlanıyor.")
                    continue
                
                # Bounding rectangle al
                x, y, w, h = cv2.boundingRect(contour)
                
                # Boyut kontrolü - çok küçük veya çok büyük olmasın
                if not (w > orig_width * 0.15 and h > orig_height * 0.15 and
                        w < orig_width * 0.98 and h < orig_height * 0.98):
                    print(f"Kontür {i+1} ({w}x{h} boyut): Boyut aralığı dışında, atlanıyor.")
                    continue

                # Boy/en oranı kontrolü (TC kimlik: 85.6mm x 53.98mm ≈ 1.586)
                aspect_ratio = w / h
                print(f"Kontür {i+1}: {w}x{h}, oran: {aspect_ratio:.2f}, alan: {area:.0f}")
                
                # Sağlamlık hesapla (contour area / convex hull area)
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                solidity = float(area) / hull_area if hull_area > 0 else 0
                print(f"Solidity: {solidity:.2f}")

                # TC kimlik kartı oranı kontrolü (yatay ve dikey desteklenir) ve sağlamlık kontrolü
                if self._is_id_card_ratio(aspect_ratio) and (solidity > 0.7):
                    # Skor hesapla: ideal orana yakınlık + sağlamlık + alan büyüklüğü
                    ideal_ratio = 1.586 if aspect_ratio > 1.0 else 1.0 / 1.586
                    ratio_score = 1.0 - min(abs(aspect_ratio - ideal_ratio) / ideal_ratio, 1.0)
                    area_score = area / (orig_width * orig_height)
                    score = ratio_score * 0.4 + solidity * 0.4 + area_score * 0.2
                    
                    print(f"✓ Uygun kart adayı bulundu: {w}x{h}, oran: {aspect_ratio:.2f}, sağlamlık: {solidity:.2f}, skor: {score:.3f}")
                    
                    if score > best_score:
                        best_score = score
                        best_candidate = (x, y, w, h)
                else:
                    print(f"Kontür {i+1}: Oran ({aspect_ratio:.2f}) veya Sağlamlık ({solidity:.2f}) uygun değil, atlanıyor.")
                
                # Alternatif: Kontürü yaklaştırarak 4 köşe ara
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 4:
                    x2, y2, w2, h2 = cv2.boundingRect(approx)
                    aspect_ratio2 = w2 / h2
                    
                    # Yaklaştırılmış kontür için sağlamlık hesapla
                    approx_hull = cv2.convexHull(approx)
                    approx_hull_area = cv2.contourArea(approx_hull)
                    approx_solidity = float(cv2.contourArea(approx)) / approx_hull_area if approx_hull_area > 0 else 0
                    print(f"Yaklaşık 4 köşeli kontür {i+1}: {w2}x{h2}, oran: {aspect_ratio2:.2f}, alan: {cv2.contourArea(approx):.0f}, sağlamlık: {approx_solidity:.2f}")

                    if (self._is_id_card_ratio(aspect_ratio2) and
                        w2 > orig_width * 0.15 and h2 > orig_height * 0.15 and
                        approx_solidity > 0.7):
                        ideal_ratio2 = 1.586 if aspect_ratio2 > 1.0 else 1.0 / 1.586
                        ratio_score2 = 1.0 - min(abs(aspect_ratio2 - ideal_ratio2) / ideal_ratio2, 1.0)
                        area_score2 = (w2 * h2) / (orig_width * orig_height)
                        # 4 köşeli kontüre bonus puan ver (daha kesin tespit)
                        score2 = ratio_score2 * 0.35 + approx_solidity * 0.35 + area_score2 * 0.2 + 0.1
                        
                        print(f"✓ 4 köşeli uygun kart adayı: {w2}x{h2}, oran: {aspect_ratio2:.2f}, sağlamlık: {approx_solidity:.2f}, skor: {score2:.3f}")
                        
                        if score2 > best_score:
                            best_score = score2
                            best_candidate = (x2, y2, w2, h2)
                    else:
                        print(f"Yaklaşık 4 köşeli kontür {i+1}: Oran ({aspect_ratio2:.2f}) veya Sağlamlık ({approx_solidity:.2f}) uygun değil, atlanıyor.")
            
            if best_candidate:
                x, y, w, h = best_candidate
                print(f"En iyi aday seçildi: {w}x{h}, skor: {best_score:.3f}")
            return best_candidate
        except Exception as e:
            print(f"Kontür analizi hatası: {str(e)}")
            return None

    def try_perspective_crop(self, image):
        """Perspektif duzeltme ile kimlik karti kirpma (egik cekilmis fotograflar icin)"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Farkli threshold degerleriyle dene
            for method in ['canny', 'adaptive']:
                if method == 'canny':
                    edges = cv2.Canny(blurred, 30, 100)
                else:
                    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                   cv2.THRESH_BINARY_INV, 11, 2)
                    edges = thresh
                
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=3)
                
                contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                
                oh, ow = image.shape[:2]
                min_area = ow * oh * 0.1
                
                for contour in contours[:10]:
                    area = cv2.contourArea(contour)
                    if area < min_area:
                        continue
                    
                    peri = cv2.arcLength(contour, True)
                    # Farkli epsilon degerleri dene
                    for eps_mult in [0.02, 0.03, 0.04, 0.05]:
                        approx = cv2.approxPolyDP(contour, eps_mult * peri, True)
                        
                        if len(approx) == 4:
                            # 4 kose bulduk - perspektif duzeltme uygula
                            pts = approx.reshape(4, 2).astype(np.float32)
                            
                            # Kosaleri sirala: sol-ust, sag-ust, sag-alt, sol-alt
                            s = pts.sum(axis=1)
                            d = np.diff(pts, axis=1)
                            tl = pts[np.argmin(s)]
                            br = pts[np.argmax(s)]
                            tr = pts[np.argmin(d)]
                            bl = pts[np.argmax(d)]
                            
                            src_pts = np.array([tl, tr, br, bl], dtype=np.float32)
                            
                            # Hedef boyutu hesapla
                            w1 = np.linalg.norm(br - bl)
                            w2 = np.linalg.norm(tr - tl)
                            h1 = np.linalg.norm(tr - br)
                            h2 = np.linalg.norm(tl - bl)
                            max_w = int(max(w1, w2))
                            max_h = int(max(h1, h2))
                            
                            if max_w < 50 or max_h < 50:
                                continue
                            
                            # Oran kontrolu
                            ratio = max_w / max_h if max_w > max_h else max_h / max_w
                            if not (1.2 < ratio < 2.0):
                                continue
                            
                            # Her zaman yatay cikti
                            if max_w < max_h:
                                max_w, max_h = max_h, max_w
                                dst_pts = np.array([
                                    [0, max_h], [0, 0], [max_w, 0], [max_w, max_h]
                                ], dtype=np.float32)
                            else:
                                dst_pts = np.array([
                                    [0, 0], [max_w, 0], [max_w, max_h], [0, max_h]
                                ], dtype=np.float32)
                            
                            M = cv2.getPerspectiveTransform(src_pts, dst_pts)
                            warped = cv2.warpPerspective(image, M, (max_w, max_h))
                            
                            print(f"Perspektif duzeltme basarili: {max_w}x{max_h}, oran: {max_w/max_h:.2f}")
                            return warped
            
            return None
        except Exception as e:
            print(f"Perspektif duzeltme hatasi: {str(e)}")
            return None

    def smart_crop_with_aspect_ratio(self, image):
        """Boy/en oranini koruyan akilli kirpma"""
        try:
            if not self.auto_crop_var.get():
                return image
            
            # Yontem 1: Kontur tabanli algilama
            card_bounds = self.detect_id_card_with_aspect_ratio(image)
            
            if card_bounds is not None:
                x, y, w, h = card_bounds
                
                # Kenar boslugu ekle (kullanici ayarindan)
                margin = int(self.margin_var.get())
                
                x_start = max(0, x - margin)
                y_start = max(0, y - margin)
                x_end = min(image.shape[1], x + w + margin)
                y_end = min(image.shape[0], y + h + margin)
                
                cropped = image[y_start:y_end, x_start:x_end]
                
                # Dikey ise yataya cevir
                crop_h, crop_w = cropped.shape[:2]
                if crop_w < crop_h:
                    print("Dikey goruntu algilandi, yatay konuma donduruluyor...")
                    cropped = cv2.rotate(cropped, cv2.ROTATE_90_COUNTERCLOCKWISE)
                
                print(f"Kimlik karti basariyla kirpildi:")
                print(f"   Orijinal: {image.shape[1]}x{image.shape[0]}")
                print(f"   Kirpilmis: {cropped.shape[1]}x{cropped.shape[0]}")
                print(f"   Kenar boslugu: {margin}px")
                return cropped
            
            # Yontem 2: Perspektif duzeltme (egik cekilmis fotograflar)
            print("Kontur tabanli algilama basarisiz, perspektif duzeltme deneniyor...")
            perspective_result = self.try_perspective_crop(image)
            if perspective_result is not None:
                return perspective_result
            
            # Yontem 3: Merkezi kirpma (son care)
            print("Perspektif duzeltme de basarisiz, merkezi kirpma uygulanacak...")
            return self.center_crop_with_ratio(image)
            
        except Exception as e:
            print(f"Akilli kirpma hatasi: {str(e)}")
            return self.center_crop_with_ratio(image)

    def center_crop_with_ratio(self, image):
        """Merkezi kırpma - kimlik kartı oranını koruyarak"""
        try:
            height, width = image.shape[:2]
            
            # Eğer dikey (portrait) ise, önce yatay konuma döndür
            if width < height:
                print("Merkezi kırpma: Dikey görüntü, yatay konuma döndürülüyor...")
                image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                height, width = image.shape[:2]
            
            # TC kimlik kartı oranı: 1.586
            target_ratio = 1.586
            current_ratio = width / height
            
            if current_ratio > target_ratio:
                # Görüntü çok geniş, yüksekliği koru, genişliği azalt
                new_width = int(height * target_ratio)
                new_height = height
                start_x = (width - new_width) // 2
                start_y = 0
            else:
                # Görüntü çok dar, genişliği koru, yüksekliği azalt
                new_width = width
                new_height = int(width / target_ratio)
                start_x = 0
                start_y = (height - new_height) // 2
            
            # Tam boyutta kirp (gereksiz alan kaybini onle)
            cropped = image[start_y:start_y + new_height, start_x:start_x + new_width]
            
            crop_h, crop_w = cropped.shape[:2]
            print(f"Merkezi kirpma uygulandi:")
            print(f"   Orijinal: {width}x{height} (oran: {current_ratio:.2f})")
            print(f"   Kirpilmis: {crop_w}x{crop_h} (oran: {crop_w/crop_h:.2f})")
            
            return cropped
            
        except Exception as e:
            print(f"Merkezi kırpma hatası: {str(e)}")
            return image

    def enhance_image(self, image):
        """Goruntu iyilestirme - siyah-beyaza cevirir ve kontrastini arttirir"""
        try:
            # Renkli ise gri tonlamaya cevir
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Kalite ayarina gore isleme siddeti belirle
            quality = int(self.quality_var.get())
            
            # Gurultu azaltma (kalite yuksekse daha agresif)
            denoise_h = max(3, min(15, int(quality / 8)))
            denoised = cv2.fastNlMeansDenoising(gray, None, h=denoise_h, templateWindowSize=7, searchWindowSize=21)
            
            # Kontrast iyilestirme - CLAHE
            clip_limit = 1.5 + (quality / 100.0) * 1.5  # 1.5 ile 3.0 arasi
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Keskinlestirme (kalite yuksekse daha fazla)
            if quality > 30:
                sharpen_amount = 0.1 + (quality / 100.0) * 0.3  # 0.1 ile 0.4 arasi
                kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]]) / 1.0
                sharpened = cv2.filter2D(enhanced, -1, kernel)
                result = cv2.addWeighted(enhanced, 1.0 - sharpen_amount, sharpened, sharpen_amount, 0)
            else:
                result = enhanced
            
            print(f"Goruntu siyah-beyaza cevrildi (kalite: {quality}%, denoise: {denoise_h}, clip: {clip_limit:.1f})")
            return result
            
        except Exception as e:
            print(f"Goruntu iyilestirme hatasi: {str(e)}")
            if len(image.shape) == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            return image

    def process_image(self, image_path, output_suffix):
        """Goruntuleri isle ve gecici dosya olarak kaydet (PDF icin)"""
        try:
            # Goruntuyu yukle (Turkce dosya yolu destegi)
            image = imread_unicode(image_path)
            if image is None:
                raise ValueError("Goruntu yuklenemedi")
            
            print(f"\n{'='*50}")
            print(f"Isleniyor: {output_suffix}")
            print(f"Orijinal goruntu boyutu: {image.shape[1]}x{image.shape[0]}")
            
            # Akilli kimlik karti kirpma
            if self.auto_crop_var.get():
                self.update_status(30, "TC kimlik karti algilaniyor...")
                cropped_image = self.smart_crop_with_aspect_ratio(image)
                print(f"Islenmis goruntu boyutu: {cropped_image.shape[1]}x{cropped_image.shape[0]}")
            else:
                cropped_image = image
                # Kirpma kapali olsa bile dikey ise yataya cevir
                ch, cw = cropped_image.shape[:2]
                if cw < ch:
                    print("Kirpma kapali ama dikey goruntu, yataya cevriliyor...")
                    cropped_image = cv2.rotate(cropped_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
                print("Otomatik kirpma kapali")
            
            # Goruntu iyilestirme (siyah-beyaza cevirme dahil)
            self.update_status(60, "Goruntu isleniyor (S/B)...")
            enhanced = self.enhance_image(cropped_image)
            
            # Son kontrol: dikey ise yataya cevir (her durumda yatay kaydet)
            if len(enhanced.shape) == 2:
                eh, ew = enhanced.shape
            else:
                eh, ew = enhanced.shape[:2]
            if ew < eh:
                print("Kayit oncesi dikey goruntu tespit edildi, yataya cevriliyor...")
                enhanced = cv2.rotate(enhanced, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            # Gecici dosya olarak kaydet (PDF olusturmak icin)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_filename = f"_temp_kimlik_{output_suffix}_{timestamp}.png"
            temp_path = os.path.join(self.temp_dir, temp_filename)
            
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # PNG olarak kaydet (kayipsiz, gecici dosya - Turkce yol destegi)
            success = imwrite_unicode(temp_path, enhanced)
            
            if not success or not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise ValueError(f"Gecici dosya olusturulamadi: {temp_path}")
            
            print(f"Gecici dosya olusturuldu: {temp_filename} ({os.path.getsize(temp_path)} byte)")
            print(f"{'='*50}\n")
            
            return temp_path
        except Exception as e:
            raise Exception(f"Islem sirasinda hata olustu: {str(e)}")

    def start_processing(self):
        # İşlemi ayrı bir thread'de başlat
        if not self.front_image_path and not self.back_image_path:
            messagebox.showwarning("Uyarı", "Lütfen en az bir görsel seçin!")
            return
        
        # İşlemi başlatmadan önce butonları devre dışı bırak
        self.toggle_buttons_state("disabled")
        
        processing_thread = threading.Thread(target=self._run_processing)
        processing_thread.start()

    def create_combined_pdf(self, image_paths):
        """On ve arka yuz goruntulerini tek bir PDF dosyasina birlestirir"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"kimlik_tam_{timestamp}.pdf"
            pdf_path = os.path.join(self.output_dir, pdf_filename)
            
            print(f"PDF olusturuluyor: {pdf_path}")
            print(f"Goruntu sayisi: {len(image_paths)}")
            for p in image_paths:
                print(f"  Kaynak: {p} (var: {os.path.exists(p)}, boyut: {os.path.getsize(p)} byte)")
            
            # Goruntuleri PIL Image olarak ac ve hepsini RGB'ye cevir
            pil_images = []
            for img_path in image_paths:
                img = Image.open(img_path)
                # Her turlu modu RGB'ye cevir (PDF sadece RGB destekler)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Dikey ise yataya cevir
                if img.width < img.height:
                    img = img.transpose(Image.ROTATE_90)
                pil_images.append(img.copy())
                img.close()
            
            if not pil_images:
                raise ValueError("PDF icin goruntu bulunamadi")
            
            # A4 sayfa boyutu (piksel cinsinden, 150 DPI): 1240 x 1754
            dpi = 150
            a4_width = int(8.27 * dpi)   # 1240 px
            a4_height = int(11.69 * dpi)  # 1754 px
            margin = int(0.5 * dpi)       # 75 px (1.27 cm)
            usable_width = a4_width - 2 * margin
            
            # A4 sayfa olustur
            page = Image.new('RGB', (a4_width, a4_height), (255, 255, 255))
            
            # Her goruntunun yukseklik payini hesapla
            card_spacing = int(0.3 * dpi)  # kartlar arasi bosluk (~0.76 cm)
            available_height = a4_height - 2 * margin
            num_images = len(pil_images)
            card_height_each = (available_height - card_spacing * (num_images - 1)) // num_images
            
            y_offset = margin
            
            for i, img in enumerate(pil_images):
                # Goruntunun en-boy oranini koru, alana sigdir
                img_ratio = img.width / img.height
                target_width = usable_width
                target_height = int(target_width / img_ratio)
                
                if target_height > card_height_each:
                    target_height = card_height_each
                    target_width = int(target_height * img_ratio)
                
                resized = img.resize((target_width, target_height), Image.LANCZOS)
                
                # Yatay ortalama
                x_pos = margin + (usable_width - target_width) // 2
                page.paste(resized, (x_pos, y_offset))
                
                print(f"  Goruntu {i+1} yerlesti: {target_width}x{target_height} @ ({x_pos}, {y_offset})")
                
                y_offset += target_height + card_spacing
            
            # PDF olarak kaydet
            page.save(pdf_path, format='PDF', resolution=dpi)
            
            # Dogrulama
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                print(f"PDF basariyla olusturuldu: {pdf_filename} ({os.path.getsize(pdf_path)} byte)")
            else:
                raise ValueError("PDF dosyasi olusturulamadi veya bos")
            
            # Son PDF yolunu sakla (yazdirma icin)
            self.last_pdf_path = pdf_path
            
            return pdf_path
            
        except Exception as e:
            print(f"PDF olusturma hatasi: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"PDF olusturulamadi: {str(e)}")

    def _run_processing(self):
        temp_files = []
        try:
            self.progress_var.set(0)
            self.update_status(10, "Islem baslatiliyor...")
            
            # Cikti klasorunu olustur
            os.makedirs(self.output_dir, exist_ok=True)
            
            if self.front_image_path:
                self.update_status(20, "On yuz isleniyor...")
                temp_path = self.process_image(self.front_image_path, "on")
                temp_files.append(temp_path)
                self.progress_var.set(40)
            
            if self.back_image_path:
                self.update_status(50, "Arka yuz isleniyor...")
                temp_path = self.process_image(self.back_image_path, "arka")
                temp_files.append(temp_path)
                self.progress_var.set(70)
            
            # PDF olustur (en az 1 goruntu varsa)
            pdf_path = None
            if temp_files:
                self.update_status(80, "PDF olusturuluyor...")
                pdf_path = self.create_combined_pdf(temp_files)
                self.progress_var.set(95)
            
            # Gecici dosyalari sil
            for tf in temp_files:
                try:
                    if os.path.exists(tf):
                        os.remove(tf)
                        print(f"Gecici dosya silindi: {tf}")
                except Exception:
                    pass
            
            self.update_status(100, "Islem tamamlandi!")
            
            # Sonuclari goster
            if pdf_path:
                pdf_size = os.path.getsize(pdf_path) / 1024
                yuz_sayisi = len(temp_files)
                result_message = f"Islem basariyla tamamlandi!\n\n"
                result_message += f"PDF dosyasi ({yuz_sayisi} yuz birlesik):\n"
                result_message += f"  {os.path.basename(pdf_path)} ({pdf_size:.1f} KB)\n"
                result_message += f"\nKlasor: {self.output_dir}"
                
                messagebox.showinfo("Basarili", result_message)
            
            self.progress_var.set(0)
            
        except Exception as e:
            # Hata durumunda da gecici dosyalari temizle
            for tf in temp_files:
                try:
                    if os.path.exists(tf):
                        os.remove(tf)
                except Exception:
                    pass
            messagebox.showerror("Islem Hatasi", str(e))
            self.update_status(0, f"Hata: {str(e)}")
            self.progress_var.set(0)
        finally:
            self.toggle_buttons_state("normal")


    def toggle_buttons_state(self, state):
        # Butonların durumunu değiştiren yardımcı fonksiyon
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Frame):
                for sub_child in child.winfo_children():
                    if isinstance(sub_child, ttk.Frame): # bottom_frame ve btn_frame
                        for btn in sub_child.winfo_children():
                            if isinstance(btn, ttk.Button):
                                btn.config(state=state)
                    # Diğer frame'lerdeki butonlar için de kontrol
                    elif isinstance(sub_child, ttk.Button):
                        sub_child.config(state=state)
        # Sadece işlem başlatma, klasör açma ve çıkış butonlarını hedeflemek daha iyi olabilir
        # Ancak bu genel çözüm şimdilik yeterli.

    def print_pdf(self):
        """Son olusturulan PDF'yi varsayilan uygulamada acar (kullanici oradan yazdirir)"""
        try:
            if not self.last_pdf_path or not os.path.exists(self.last_pdf_path):
                messagebox.showwarning("Uyari", 
                    "Yazdirilacak PDF bulunamadi.\nOnce 'Islemi Baslat' ile kimlik isleyin.")
                return
            
            pdf_path = os.path.normpath(self.last_pdf_path)
            system = platform.system()
            
            if system == 'Windows':
                os.startfile(pdf_path)
            elif system == 'Darwin':
                subprocess.Popen(['open', pdf_path])
            else:
                subprocess.Popen(['xdg-open', pdf_path])
            
            self.update_status(0, "PDF acildi - Ctrl+P ile yazdiriniz")
                
        except Exception as e:
            messagebox.showerror("Yazdirma Hatasi", 
                f"PDF acilamadi:\n{str(e)}\n\n"
                f"PDF dosyasi: {self.last_pdf_path}\n"
                f"Dosyayi manuel olarak acip yazdiriniz.")

    def open_output_folder(self):
        """Cikti klasorunu ac"""
        try:
            if os.path.exists(self.output_dir):
                os.startfile(self.output_dir)
            else:
                messagebox.showinfo("Bilgi", f"Klasör henüz oluşturulmadı:\n{self.output_dir}")
        except Exception as e:
            messagebox.showerror("Hata", f"Klasör açılamadı: {str(e)}")

    def update_status(self, progress, message):
        self.progress_var.set(progress)
        self.status_label.config(text=message)
        self.root.update_idletasks() # UI'yı hemen güncelle

    def cleanup_and_exit(self):
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Temizleme hatası: {str(e)}")
        finally:
            self.root.quit() # Tkinter uygulamasını güvenli bir şekilde kapat

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.cleanup_and_exit) # Pencere kapatma olayını yakala
        self.root.mainloop()

if __name__ == "__main__":
    print("TC Kimlik Kartı Düzenleyici v1 by SWAPNIL")
    print("=" * 60)
    print("Özellikler:")
    print("  Boy/En oranını koruyan akıllı kırpma (yatay + dikey destek)")
    print("  Çoklu algılama yöntemi (Canny, Adaptive, Gradient)")
    print("  TC kimlik kartı oranı kontrolü (1.586)")
    print("  Ayarlanabilir minimum kart boyutu")
    print("  Merkezi yedek kırpma sistemi")
    print("  Ön ve arka yüzü tek PDF'ye birleştirme")
    print("  Detaylı işlem logları")
    print("=" * 60)
    
    app = IDCardProcessor()
    app.run()
