import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps
import threading
import sys
from datetime import datetime
import shutil

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
        self.min_size_var = tk.DoubleVar(value=0.15)
        size_scale = ttk.Scale(settings_frame, from_=0.05, to=0.5, variable=self.min_size_var, orient=tk.HORIZONTAL)
        size_scale.grid(row=2, column=1, padx=5, sticky='ew') # Yatayda genişle
        self.size_label = ttk.Label(settings_frame, text="15%")
        self.size_label.grid(row=2, column=2, padx=5)
        size_scale.configure(command=self.update_size_label)
        
        ttk.Label(settings_frame, text="Görüntü Kalitesi:").grid(row=3, column=0, padx=5, sticky='w')
        self.quality_var = tk.IntVar(value=95)
        # Görüntü kalitesi ayarını %0'dan (kapalı) %100'e kadar düzenledim.
        quality_scale = ttk.Scale(settings_frame, from_=0, to=100, variable=self.quality_var, orient=tk.HORIZONTAL)
        quality_scale.grid(row=3, column=1, padx=5, sticky='ew') # Yatayda genişle
        self.quality_label = ttk.Label(settings_frame, text="95%")
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
        btn_frame.grid(row=1, column=1, sticky="e") # Butonları sağa hizala
        
        ttk.Button(btn_frame, text="Klasörü Aç", 
                   command=self.open_output_folder).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="İşlemi Başlat", 
                   command=self.start_processing).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Çıkış", 
                   command=self.cleanup_and_exit).pack(side=tk.RIGHT, padx=5)

    def update_margin_label(self, value):
        self.margin_label.config(text=f"{int(float(value))}px")
    
    def update_size_label(self, value):
        self.size_label.config(text=f"{int(float(value)*100)}%")
    
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
            
            temp_path = os.path.join(self.temp_dir, f"{side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")
            shutil.copy2(file_path, temp_path)
            
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
            
            # RGBA (şeffaf) görüntüleri RGB'ye dönüştürerek arka plan sorunlarını önle
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

    def analyze_contours(self, contours, orig_width, orig_height):
        """Kontürleri analiz et ve en uygun kimlik kartını bul"""
        try:
            # Kontürleri alan büyüklüğüne göre sırala
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            min_area_ratio = self.min_size_var.get()
            min_area = (orig_width * orig_height) * min_area_ratio
            
            print(f"Minimum alan: {min_area} (görüntünün %{min_area_ratio*100:.1f}'i)")
            
            # En büyük 15 kontürü kontrol et
            for i, contour in enumerate(contours[:15]):
                area = cv2.contourArea(contour)
                
                if area < min_area:
                    print(f"Kontür {i+1} ({area:.0f} alan): Alan çok küçük, atlanıyor.")
                    continue
                
                # Bounding rectangle al
                x, y, w, h = cv2.boundingRect(contour)
                
                # Boyut kontrolü - çok küçük veya çok büyük olmasın
                if not (w > orig_width * 0.2 and h > orig_height * 0.15 and
                        w < orig_width * 0.95 and h < orig_height * 0.95):
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

                # TC kimlik kartı oranı kontrolü (yeniden genişletilmiş aralık: 1.3 - 2.0) ve sağlamlık kontrolü
                # Bu aralık, barkodun dahil edilmesiyle oluşabilecek küçük sapmaları tolere eder.
                if (1.3 < aspect_ratio < 2.0) and (solidity > 0.9):
                    print(f"✓ Uygun kart bulundu: {w}x{h}, oran: {aspect_ratio:.2f}, sağlamlık: {solidity:.2f}")
                    return x, y, w, h
                else:
                    print(f"Kontür {i+1}: Oran ({aspect_ratio:.2f}) veya Sağlamlık ({solidity:.2f}) uygun değil, atlanıyor.")
                
                # Alternatif: Kontürü yaklaştırarak 4 köşe ara
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = w / h
                    
                    # Yaklaştırılmış kontür için sağlamlık hesapla
                    approx_hull = cv2.convexHull(approx)
                    approx_hull_area = cv2.contourArea(approx_hull)
                    approx_solidity = float(cv2.contourArea(approx)) / approx_hull_area if approx_hull_area > 0 else 0
                    print(f"Yaklaşık 4 köşeli kontür {i+1}: {w}x{h}, oran: {aspect_ratio:.2f}, alan: {cv2.contourArea(approx):.0f}, sağlamlık: {approx_solidity:.2f}")

                    if (1.3 < aspect_ratio < 2.0 and # Yine daha esnek oran
                        w > orig_width * 0.2 and h > orig_height * 0.15 and
                        approx_solidity > 0.9): # Sağlamlık kontrolü
                        print(f"✓ 4 köşeli uygun kart bulundu: {w}x{h}, oran: {aspect_ratio:.2f}, sağlamlık: {approx_solidity:.2f}")
                        return x, y, w, h
                    else:
                        print(f"Yaklaşık 4 köşeli kontür {i+1} (yaklaşık): Oran ({aspect_ratio:.2f}) veya Sağlamlık ({approx_solidity:.2f}) uygun değil, atlanıyor.")
            
            return None
        except Exception as e:
            print(f"Kontür analizi hatası: {str(e)}")
            return None

    def smart_crop_with_aspect_ratio(self, image):
        """Boy/en oranını koruyan akıllı kırpma"""
        try:
            if not self.auto_crop_var.get():
                return image
            
            # Kimlik kartı sınırlarını algıla
            card_bounds = self.detect_id_card_with_aspect_ratio(image)
            
            if card_bounds is None:
                print("Kimlik kartı algılanamadı, merkezi kırpma uygulanıyor...")
                return self.center_crop_with_ratio(image)
            
            x, y, w, h = card_bounds
            
            # Kenar boşluğu ekle
            margin = int(self.margin_var.get())
            
            # Sınırları genişlet (boy ve en için ayrı ayrı)
            x_start = max(0, x - margin)
            y_start = max(0, y - margin)
            x_end = min(image.shape[1], x + w + margin)
            y_end = min(image.shape[0], y + h + margin)
            
            # Kırp
            cropped = image[y_start:y_end, x_start:x_end]
            
            print(f"Kimlik kartı başarıyla kırpıldı:")
            print(f"   Orijinal: {image.shape[1]}x{image.shape[0]}")
            print(f"   Kırpılmış: {cropped.shape[1]}x{cropped.shape[0]}")
            print(f"   Konum: ({x_start},{y_start}) -> ({x_end},{y_end})")
            
            return cropped
            
        except Exception as e:
            print(f"Akıllı kırpma hatası: {str(e)}")
            return self.center_crop_with_ratio(image)

    def center_crop_with_ratio(self, image):
        """Merkezi kırpma - kimlik kartı oranını koruyarak"""
        try:
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
            
            # %80'ini al (çok agresif kırpma yapma)
            crop_factor = 0.8
            final_width = int(new_width * crop_factor)
            final_height = int(new_height * crop_factor)
            
            start_x += (new_width - final_width) // 2
            start_y += (new_height - final_height) // 2
            
            cropped = image[start_y:start_y + final_height, start_x:start_x + final_width]
            
            print(f"Merkezi kırpma uygulandı:")
            print(f"   Orijinal: {width}x{height} (oran: {current_ratio:.2f})")
            print(f"   Kırpılmış: {final_width}x{final_height} (oran: {final_width/final_height:.2f})")
            
            return cropped
            
        except Exception as e:
            print(f"Merkezi kırpma hatası: {str(e)}")
            return image

    def enhance_image(self, image):
        """Görüntü iyileştirme"""
        try:
            # Eğer renkli görüntüyse, gri tonlamalı yap
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Gürültü azaltma
            denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
            
            # Kontrast iyileştirme
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(denoised)
            
            # Hafif keskinleştirme
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]]) / 1.0
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # Orijinal ile karıştır
            result = cv2.addWeighted(enhanced, 0.8, sharpened, 0.2, 0)
            
            return result
            
        except Exception as e:
            print(f"Görüntü iyileştirme hatası: {str(e)}")
            return image

    def process_image(self, image_path, output_suffix):
        try:
            # Görüntüyü yükle
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Görüntü yüklenemedi")
            
            print(f"\n{'='*50}")
            print(f"İşleniyor: {output_suffix}")
            print(f"Orijinal görüntü boyutu: {image.shape[1]}x{image.shape[0]}")
            
            # Akıllı kimlik kartı kırpma
            if self.auto_crop_var.get():
                self.update_status(30, "TC kimlik kartı algılanıyor (boy/en oranı korunuyor)...")
                cropped_image = self.smart_crop_with_aspect_ratio(image)
                print(f"İşlenmiş görüntü boyutu: {cropped_image.shape[1]}x{cropped_image.shape[0]}")
            else:
                cropped_image = image
                print("Otomatik kırpma kapalı")
            
            # Görüntü iyileştirme
            self.update_status(60, "Görüntü iyileştiriliyor...")
            enhanced = self.enhance_image(cropped_image)
            
            # Çıktı dosya yolunu oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"kimlik_{output_suffix}_{timestamp}.jpg"
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Klasörün var olduğundan emin ol
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Görüntüyü kaydet
            quality = int(self.quality_var.get())
            # Eğer kalite 0 ise, sıkıştırma yapmadan kaydedin veya özel bir işlem yapın.
            # JPEG kalitesi 0-100 arasında olmalıdır. Eğer 0 verilirse, bazı kütüphaneler hata verebilir.
            # Bu durumda, 0'ı özel bir "kalite yok" durumu olarak ele alabiliriz.
            if quality == 0:
                # Kalite 0 ise, daha az sıkıştırmalı veya sıkıştırmasız bir format düşünebiliriz.
                # Ancak JPEG için 0, genellikle en düşük kalite anlamına gelir.
                # Eğer kullanıcı "kapalı" derken hiç işlem yapılmamasını kastediyorsa,
                # bu kısmı daha farklı ele almak gerekebilir.
                # Şimdilik, 0'ı doğrudan JPEG kalitesi olarak kullanmaya devam edelim.
                # OpenCV'nin imwrite fonksiyonu 0 kalitesini kabul eder.
                success = cv2.imwrite(output_path, enhanced, [int(cv2.IMWRITE_JPEG_QUALITY), 0])
            else:
                success = cv2.imwrite(output_path, enhanced, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            
            if not success:
                raise ValueError(f"Görüntü kaydedilemedi: {output_path}")
            
            # Kaydedilen dosyayı kontrol et
            if not os.path.exists(output_path):
                raise ValueError(f"Dosya oluşturulamadı: {output_path}")
            
            # Dosya boyutunu kontrol et
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise ValueError(f"Boş dosya oluşturuldu: {output_path}")
            
            print(f"✓ Başarıyla kaydedildi: {output_filename}")
            print(f"{'='*50}\n")
            
            return output_path
        except Exception as e:
            raise Exception(f"İşlem sırasında hata oluştu: {str(e)}")

    def start_processing(self):
        # İşlemi ayrı bir thread'de başlat
        if not self.front_image_path and not self.back_image_path:
            messagebox.showwarning("Uyarı", "Lütfen en az bir görsel seçin!")
            return
        
        # İşlemi başlatmadan önce butonları devre dışı bırak
        self.toggle_buttons_state("disabled")
        
        processing_thread = threading.Thread(target=self._run_processing)
        processing_thread.start()

    def _run_processing(self):
        try:
            self.progress_var.set(0)
            self.update_status(10, "İşlem başlatılıyor...")
            
            # Çıktı klasörünü oluştur
            os.makedirs(self.output_dir, exist_ok=True)
            
            processed_files = []
            
            if self.front_image_path:
                self.update_status(20, "Ön yüz işleniyor...")
                output_path = self.process_image(self.front_image_path, "on")
                processed_files.append(output_path)
                self.progress_var.set(50)
            
            if self.back_image_path:
                self.update_status(70, "Arka yüz işleniyor...")
                output_path = self.process_image(self.back_image_path, "arka")
                processed_files.append(output_path)
                self.progress_var.set(90)
            
            self.update_status(100, "İşlem tamamlandı!")
            
            # Sonuçları göster
            result_message = f"İşlem başarıyla tamamlandı!\n\n"
            result_message += f"Kaydedilen dosyalar ({len(processed_files)} adet):\n"
            for file_path in processed_files:
                file_size = os.path.getsize(file_path) / 1024  # KB cinsinden
                result_message += f"• {os.path.basename(file_path)} ({file_size:.1f} KB)\n"
            result_message += f"\nKlasör: {self.output_dir}"
            
            messagebox.showinfo("Başarılı", result_message)
            self.progress_var.set(0)
            
        except Exception as e:
            messagebox.showerror("İşlem Hatası", str(e))
            self.update_status(0, f"Hata: {str(e)}")
            self.progress_var.set(0)
        finally:
            # İşlem bitince butonları tekrar etkinleştir
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

    def open_output_folder(self):
        """Çıktı klasörünü aç"""
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
    print("• Boy/En oranını koruyan akıllı kırpma")
    print("• Çoklu algılama yöntemi (Canny, Adaptive, Gradient)")
    print("• TC kimlik kartı oranı kontrolü (1.586)")
    print("• Ayarlanabilir minimum kart boyutu")
    print("• Merkezi yedek kırpma sistemi")
    print("• Detaylı işlem logları")
    print("=" * 60)
    
    app = IDCardProcessor()
    app.run()
