# -*- coding: utf-8 -*-
import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFont
import PIL.PdfImagePlugin
import threading
import sys
import subprocess
import platform
from datetime import datetime
import shutil


# ---------------------------------------------------------------------------
# Turkce dosya yolu destegi icin yardimci fonksiyonlar
# ---------------------------------------------------------------------------
def imread_unicode(path):
    try:
        img = cv2.imread(path)
        if img is not None:
            return img
    except Exception:
        pass
    try:
        pil_img = Image.open(path)
        if pil_img.mode == 'RGBA':
            pil_img = pil_img.convert('RGB')
        arr = np.array(pil_img)
        if len(arr.shape) == 3:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return arr
    except Exception as e:
        print(f"Goruntu okunamadi: {path} - {e}")
        return None


def imwrite_unicode(path, img):
    try:
        ok = cv2.imwrite(path, img)
        if ok:
            return True
    except Exception:
        pass
    try:
        if len(img.shape) == 2:
            pil_img = Image.fromarray(img, mode='L')
        else:
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        pil_img.save(path)
        return True
    except Exception as e:
        print(f"Goruntu kaydedilemedi: {path} - {e}")
        return False


# ---------------------------------------------------------------------------
# Renk paleti
# ---------------------------------------------------------------------------
C_BG        = '#1A1A2E'      # Ana arka plan
C_SURFACE   = '#16213E'      # Kart/panel arka plani
C_SURFACE2  = '#0F3460'      # Vurgulu panel
C_ACCENT    = '#E94560'      # Ana vurgu (kirmizi-pembe)
C_ACCENT2   = '#533483'      # Ikincil vurgu (mor)
C_TEXT      = '#EAEAEA'       # Ana metin
C_TEXT_DIM  = '#8892B0'       # Soluk metin
C_SUCCESS   = '#00D68F'       # Basari yesili
C_BORDER    = '#2A2A4A'       # Cerceve kenarligi


class IDCardProcessor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('TC Kimlik Kart\u0131 D\u00fczenleyici')
        self.root.geometry('1080x820')
        self.root.minsize(960, 720)
        self.root.configure(bg=C_BG)

        # ---- ikon ----
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath('.')
        for ico in ('app_icon.png', 'app.ico'):
            p = os.path.join(base_path, ico)
            if os.path.exists(p):
                try:
                    if ico.endswith('.png'):
                        ph = ImageTk.PhotoImage(Image.open(p).resize((64, 64), Image.LANCZOS))
                        self.root.iconphoto(True, ph)
                    else:
                        self.root.iconbitmap(p)
                    break
                except Exception:
                    pass

        # ---- degiskenler ----
        self.temp_dir = os.path.join(os.getenv('TEMP', '/tmp'), 'kimlik_islemleri')
        self.front_image_path = ''
        self.back_image_path = ''
        self.last_pdf_path = ''
        docs = os.path.join(os.path.expanduser('~'), 'Documents')
        self.output_dir = os.path.join(docs, 'TC_Kimlik_Islemleri')
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self._setup_styles()
        self._build_ui()

    # ------------------------------------------------------------------
    # STILLER
    # ------------------------------------------------------------------
    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.style.configure('.', background=C_BG, foreground=C_TEXT,
                             font=('Segoe UI', 10))
        self.style.configure('TFrame', background=C_BG)
        self.style.configure('Surface.TFrame', background=C_SURFACE)

        # LabelFrame
        self.style.configure('TLabelframe', background=C_SURFACE, borderwidth=2,
                             relief='groove')
        self.style.configure('TLabelframe.Label', background=C_SURFACE,
                             foreground=C_ACCENT, font=('Segoe UI', 10, 'bold'))

        # Label
        self.style.configure('TLabel', background=C_BG, foreground=C_TEXT,
                             font=('Segoe UI', 10))
        self.style.configure('Dim.TLabel', background=C_BG, foreground=C_TEXT_DIM,
                             font=('Segoe UI', 9))
        self.style.configure('SurfaceLabel.TLabel', background=C_SURFACE,
                             foreground=C_TEXT, font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', background=C_SURFACE,
                             foreground=C_TEXT_DIM, font=('Segoe UI', 12))
        self.style.configure('Header.TLabel', background=C_BG,
                             foreground=C_TEXT, font=('Segoe UI', 18, 'bold'))
        self.style.configure('Success.TLabel', background=C_BG,
                             foreground=C_SUCCESS, font=('Segoe UI', 9))

        # Checkbutton
        self.style.configure('TCheckbutton', background=C_SURFACE,
                             foreground=C_TEXT, font=('Segoe UI', 10))

        # Button
        self.style.configure('TButton', background=C_SURFACE2,
                             foreground=C_TEXT, font=('Segoe UI', 10),
                             padding=(14, 7), borderwidth=0)
        self.style.map('TButton',
                        background=[('active', C_ACCENT2), ('disabled', C_BORDER)])

        self.style.configure('Accent.TButton', background=C_ACCENT,
                             foreground='#FFFFFF', font=('Segoe UI', 11, 'bold'),
                             padding=(20, 10), borderwidth=0)
        self.style.map('Accent.TButton',
                        background=[('active', '#C73E54'), ('disabled', C_BORDER)])

        # Progressbar
        self.style.configure('TProgressbar', thickness=6,
                             troughcolor=C_SURFACE, background=C_ACCENT)

        # Scale
        self.style.configure('TScale', background=C_SURFACE,
                             troughcolor=C_SURFACE2)

    # ------------------------------------------------------------------
    # ARAYUZ
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = self.root
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        outer = ttk.Frame(root, padding=16)
        outer.grid(row=0, column=0, sticky='nsew')
        outer.grid_columnconfigure(0, weight=1)
        # satirlar: 0=header  1=dosya  2=kayit  3=ayarlar  4=onizleme(genisler) 5=alt
        outer.grid_rowconfigure(4, weight=1)

        # ---- BASLIK ----
        hdr = ttk.Frame(outer)
        hdr.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        ttk.Label(hdr, text='TC Kimlik Kart\u0131 D\u00fczenleyici',
                  style='Header.TLabel').pack(side='left')
        ttk.Label(hdr, text='v2  \u2022  by SWAPNIL', style='Dim.TLabel').pack(
            side='left', padx=(10, 0), pady=(8, 0))

        # ---- DOSYA SECIMI ----
        fsel = ttk.LabelFrame(outer, text=' Dosya Se\u00e7imi ', padding=12)
        fsel.grid(row=1, column=0, sticky='ew', pady=4)
        fsel.grid_columnconfigure(1, weight=1)

        ttk.Button(fsel, text='\u00d6n Y\u00fcz Se\u00e7',
                   command=lambda: self.select_image('front')).grid(
            row=0, column=0, padx=(0, 8), pady=3, sticky='w')
        self.front_label = ttk.Label(fsel, text='Se\u00e7ili dosya yok',
                                     style='SurfaceLabel.TLabel')
        self.front_label.grid(row=0, column=1, sticky='ew')

        ttk.Button(fsel, text='Arka Y\u00fcz Se\u00e7',
                   command=lambda: self.select_image('back')).grid(
            row=1, column=0, padx=(0, 8), pady=3, sticky='w')
        self.back_label = ttk.Label(fsel, text='Se\u00e7ili dosya yok',
                                    style='SurfaceLabel.TLabel')
        self.back_label.grid(row=1, column=1, sticky='ew')

        # ---- KAYIT BILGISI ----
        info = ttk.LabelFrame(outer, text=' Kay\u0131t Bilgisi ', padding=12)
        info.grid(row=2, column=0, sticky='ew', pady=4)

        ttk.Label(info, text='Dosyalar \u015furaya kaydedilecek:',
                  style='SurfaceLabel.TLabel').pack(anchor='w')

        prow = ttk.Frame(info)
        prow.configure(style='Surface.TFrame')
        prow.pack(anchor='w', fill='x', padx=(16, 0), pady=(4, 0))

        self.path_label = tk.Label(prow, text=self.output_dir,
                                    fg=C_ACCENT, bg=C_SURFACE, cursor='hand2',
                                    font=('Segoe UI', 9, 'underline'))
        self.path_label.pack(side='left')
        self.path_label.bind('<Button-1>', self._copy_path)
        self.path_label.bind('<Enter>', lambda e: self.path_label.config(fg='#FF6B81'))
        self.path_label.bind('<Leave>', lambda e: self.path_label.config(fg=C_ACCENT))

        self.clip_lbl = ttk.Label(prow, text='', style='Success.TLabel')
        self.clip_lbl.configure(background=C_SURFACE)
        self.clip_lbl.pack(side='left', padx=(12, 0))

        # ---- AYARLAR ----
        sett = ttk.LabelFrame(outer, text=' \u0130\u015flem Ayarlar\u0131 ', padding=12)
        sett.grid(row=3, column=0, sticky='ew', pady=4)
        sett.grid_columnconfigure(1, weight=1)

        self.auto_crop_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(sett, text='Ak\u0131ll\u0131 Kimlik Alg\u0131lama ve K\u0131rpma',
                        variable=self.auto_crop_var).grid(
            row=0, column=0, columnspan=3, sticky='w', padx=4, pady=2)

        # Kenar boslugu
        ttk.Label(sett, text='Kenar Bo\u015flu\u011fu:', style='SurfaceLabel.TLabel').grid(
            row=1, column=0, padx=4, sticky='w')
        self.margin_var = tk.IntVar(value=10)
        ms = ttk.Scale(sett, from_=0, to=50, variable=self.margin_var,
                       orient=tk.HORIZONTAL)
        ms.grid(row=1, column=1, padx=4, sticky='ew')
        self.margin_lbl = ttk.Label(sett, text='10 px', width=7,
                                    style='SurfaceLabel.TLabel')
        self.margin_lbl.grid(row=1, column=2, padx=4)
        ms.configure(command=lambda v: self.margin_lbl.config(
            text=f'{int(float(v))} px'))

        # PDF kart boyutu
        ttk.Label(sett, text='PDF Kart Boyutu:', style='SurfaceLabel.TLabel').grid(
            row=2, column=0, padx=4, sticky='w')
        self.pdf_scale_var = tk.IntVar(value=90)
        ps = ttk.Scale(sett, from_=30, to=100, variable=self.pdf_scale_var,
                       orient=tk.HORIZONTAL)
        ps.grid(row=2, column=1, padx=4, sticky='ew')
        self.size_lbl = ttk.Label(sett, text='%90', width=7,
                                  style='SurfaceLabel.TLabel')
        self.size_lbl.grid(row=2, column=2, padx=4)
        ps.configure(command=lambda v: self.size_lbl.config(
            text=f'%{int(float(v))}'))

        # Iyilestirme seviyesi
        ttk.Label(sett, text='\u0130yile\u015ftirme:', style='SurfaceLabel.TLabel').grid(
            row=3, column=0, padx=4, sticky='w')
        self.quality_var = tk.IntVar(value=70)
        qs = ttk.Scale(sett, from_=10, to=100, variable=self.quality_var,
                       orient=tk.HORIZONTAL)
        qs.grid(row=3, column=1, padx=4, sticky='ew')
        self.qual_lbl = ttk.Label(sett, text='%70', width=7,
                                  style='SurfaceLabel.TLabel')
        self.qual_lbl.grid(row=3, column=2, padx=4)
        qs.configure(command=lambda v: self.qual_lbl.config(
            text=f'%{int(float(v))}'))

        # ---- ONIZLEME ----
        prev = ttk.LabelFrame(outer, text=' \u00d6nizleme ', padding=10)
        prev.grid(row=4, column=0, sticky='nsew', pady=4)
        prev.grid_columnconfigure(0, weight=1)
        prev.grid_columnconfigure(1, weight=1)
        prev.grid_rowconfigure(0, weight=1)

        self.front_frame = ttk.Frame(prev, style='Surface.TFrame')
        self.front_frame.grid(row=0, column=0, sticky='nsew', padx=4, pady=4)
        self.front_frame.grid_propagate(False)
        self.front_view = ttk.Label(self.front_frame,
                                     text='\u00d6n Y\u00fcz\nDosya se\u00e7ilmedi',
                                     justify=tk.CENTER, style='Title.TLabel')
        self.front_view.pack(fill='both', expand=True)

        self.back_frame = ttk.Frame(prev, style='Surface.TFrame')
        self.back_frame.grid(row=0, column=1, sticky='nsew', padx=4, pady=4)
        self.back_frame.grid_propagate(False)
        self.back_view = ttk.Label(self.back_frame,
                                    text='Arka Y\u00fcz\nDosya se\u00e7ilmedi',
                                    justify=tk.CENTER, style='Title.TLabel')
        self.back_view.pack(fill='both', expand=True)

        # ---- ALT BAR ----
        bot = ttk.Frame(outer)
        bot.grid(row=5, column=0, sticky='ew', pady=(8, 0))
        bot.grid_columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(bot, variable=self.progress_var, maximum=100).grid(
            row=0, column=0, columnspan=2, sticky='ew', pady=(0, 6))

        self.status_label = ttk.Label(bot, text='Haz\u0131r', style='Dim.TLabel')
        self.status_label.grid(row=1, column=0, sticky='w')

        bfr = ttk.Frame(bot)
        bfr.grid(row=1, column=1, sticky='e')

        ttk.Button(bfr, text='\u0130\u015flemi Ba\u015flat', style='Accent.TButton',
                   command=self.start_processing).pack(side='right', padx=4)
        ttk.Button(bfr, text='Yazd\u0131r',
                   command=self.print_pdf).pack(side='right', padx=4)
        ttk.Button(bfr, text='Klas\u00f6r\u00fc A\u00e7',
                   command=self.open_output_folder).pack(side='right', padx=4)
        ttk.Button(bfr, text='\u00c7\u0131k\u0131\u015f',
                   command=self.cleanup_and_exit).pack(side='right', padx=4)

    # ------------------------------------------------------------------
    # YARDIMCI
    # ------------------------------------------------------------------
    def _copy_path(self, _=None):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.output_dir)
        self.clip_lbl.config(text='Panoya kopyaland\u0131!')
        self.clip_lbl.configure(background=C_SURFACE)
        self.root.after(2500, lambda: self.clip_lbl.config(text=''))

    def update_status(self, progress, msg):
        self.progress_var.set(progress)
        self.status_label.config(text=msg)
        self.root.update_idletasks()

    # ------------------------------------------------------------------
    # DOSYA SECIMI
    # ------------------------------------------------------------------
    def select_image(self, side):
        try:
            path = filedialog.askopenfilename(
                title=f'TC Kimlik {"On" if side == "front" else "Arka"} Y\u00fcz\u00fc Se\u00e7in',
                filetypes=[('Resim Dosyalar\u0131', '*.jpg *.jpeg *.png *.bmp'),
                           ('T\u00fcm Dosyalar', '*.*')])
            if not path:
                return

            ext = os.path.splitext(path)[1].lower()
            if ext not in ('.jpg', '.jpeg', '.png', '.bmp'):
                raise ValueError('Desteklenmeyen format. JPG, PNG veya BMP se\u00e7in.')

            with Image.open(path) as im:
                im.verify()

            safe = f'{side}_{datetime.now().strftime("%Y%m%d_%H%M%S")}{ext}'
            tmp = os.path.join(self.temp_dir, safe)
            try:
                shutil.copy2(path, tmp)
            except Exception:
                Image.open(path).save(tmp)

            if side == 'front':
                self.front_image_path = tmp
                self.front_label.config(text=os.path.basename(path))
                self._show_preview(tmp, self.front_view)
            else:
                self.back_image_path = tmp
                self.back_label.config(text=os.path.basename(path))
                self._show_preview(tmp, self.back_view)

            self.update_status(0, f'{"On" if side == "front" else "Arka"} y\u00fcz y\u00fcklendi')
        except Exception as e:
            messagebox.showerror('Hata', str(e))

    def _show_preview(self, path, label):
        try:
            label.master.update_idletasks()
            fw = max(label.master.winfo_width(), 200)
            fh = max(label.master.winfo_height(), 200)
            img = Image.open(path)
            img.thumbnail((fw, fh), Image.LANCZOS)
            if img.mode in ('RGBA', 'LA'):
                bg = Image.new('RGB', img.size, (22, 33, 62))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            ph = ImageTk.PhotoImage(img)
            label.config(image=ph, text='')
            label.image = ph
        except Exception as e:
            label.config(image='', text=f'Hata:\n{e}')

    # ------------------------------------------------------------------
    # ALGILAMA + KIRPMA + ARKA PLAN SILME
    # ------------------------------------------------------------------
    def detect_id_card(self, image):
        """TC Kimlik kartini algilar, kirpar VE standart boyuta esneterek dondurur."""
        oh, ow = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Coklu yontemle dene
        for method_fn in (self._det_canny, self._det_adaptive, self._det_gradient):
            res = method_fn(gray, ow, oh)
            if res is not None:
                return res
        return None

    def _det_canny(self, gray, ow, oh):
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        for lo in (30, 50, 70):
            for hi in (80, 120, 150):
                edges = cv2.Canny(blurred, lo, hi, apertureSize=3)
                k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                cl = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k, iterations=2)
                cnts, _ = cv2.findContours(cl, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
                r = self._best_contour(cnts, ow, oh)
                if r is not None:
                    return r
        return None

    def _det_adaptive(self, gray, ow, oh):
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        m = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k, iterations=3)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._best_contour(cnts, ow, oh)

    def _det_gradient(self, gray, ow, oh):
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        mag = np.sqrt(gx ** 2 + gy ** 2)
        mag = np.uint8(mag / mag.max() * 255)
        _, th = cv2.threshold(mag, 50, 255, cv2.THRESH_BINARY)
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        m = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k, iterations=2)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._best_contour(cnts, ow, oh)

    @staticmethod
    def _is_card_ratio(ar):
        return (1.2 < ar < 2.0) or (0.5 < ar < 0.83)

    def _best_contour(self, contours, ow, oh):
        if not contours:
            return None
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        min_area = ow * oh * 0.08
        best, bscore = None, 0.0

        for cnt in contours[:15]:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            if w < ow * 0.12 or h < oh * 0.12 or w > ow * 0.98 or h > oh * 0.98:
                continue
            ar = w / h
            hull = cv2.convexHull(cnt)
            ha = cv2.contourArea(hull)
            sol = float(area) / ha if ha > 0 else 0

            if self._is_card_ratio(ar) and sol > 0.65:
                ideal = 1.586 if ar > 1.0 else 1.0 / 1.586
                rs = 1.0 - min(abs(ar - ideal) / ideal, 1.0)
                sc = rs * 0.4 + sol * 0.3 + (area / (ow * oh)) * 0.3
                if sc > bscore:
                    bscore = sc
                    best = (x, y, w, h)

            # 4 kose yaklasimlama
            eps = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, eps, True)
            if len(approx) == 4:
                x2, y2, w2, h2 = cv2.boundingRect(approx)
                ar2 = w2 / h2
                ah = cv2.convexHull(approx)
                aha = cv2.contourArea(ah)
                asol = float(cv2.contourArea(approx)) / aha if aha > 0 else 0
                if self._is_card_ratio(ar2) and asol > 0.65:
                    ideal2 = 1.586 if ar2 > 1.0 else 1.0 / 1.586
                    rs2 = 1.0 - min(abs(ar2 - ideal2) / ideal2, 1.0)
                    sc2 = rs2 * 0.35 + asol * 0.3 + (w2 * h2) / (ow * oh) * 0.25 + 0.1
                    if sc2 > bscore:
                        bscore = sc2
                        best = (x2, y2, w2, h2)
        return best

    def _perspective_crop(self, image):
        """Egik cekilmis goruntuler icin perspektif duzeltme"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            oh, ow = image.shape[:2]
            min_a = ow * oh * 0.08

            for meth in ('canny', 'adaptive'):
                if meth == 'canny':
                    edges = cv2.Canny(blur, 30, 100)
                else:
                    edges = cv2.adaptiveThreshold(blur, 255,
                                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                   cv2.THRESH_BINARY_INV, 11, 2)
                k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                cl = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k, iterations=3)
                cnts, _ = cv2.findContours(cl, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
                cnts = sorted(cnts, key=cv2.contourArea, reverse=True)

                for cnt in cnts[:10]:
                    if cv2.contourArea(cnt) < min_a:
                        continue
                    peri = cv2.arcLength(cnt, True)
                    for em in (0.02, 0.03, 0.04, 0.05):
                        ap = cv2.approxPolyDP(cnt, em * peri, True)
                        if len(ap) != 4:
                            continue
                        pts = ap.reshape(4, 2).astype(np.float32)
                        s = pts.sum(axis=1)
                        d = np.diff(pts, axis=1)
                        tl, br = pts[np.argmin(s)], pts[np.argmax(s)]
                        tr, bl = pts[np.argmin(d)], pts[np.argmax(d)]
                        src = np.array([tl, tr, br, bl], dtype=np.float32)
                        mw = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
                        mh = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
                        if mw < 50 or mh < 50:
                            continue
                        ratio = mw / mh if mw > mh else mh / mw
                        if not (1.2 < ratio < 2.0):
                            continue
                        if mw < mh:
                            mw, mh = mh, mw
                            dst = np.array([[0, mh], [0, 0], [mw, 0], [mw, mh]],
                                           dtype=np.float32)
                        else:
                            dst = np.array([[0, 0], [mw, 0], [mw, mh], [0, mh]],
                                           dtype=np.float32)
                        M = cv2.getPerspectiveTransform(src, dst)
                        return cv2.warpPerspective(image, M, (mw, mh))
        except Exception:
            pass
        return None

    def _remove_background(self, image):
        """GrabCut ile kimlik karti cevresindeki arka plani beyaza cevir"""
        try:
            h, w = image.shape[:2]
            mask = np.zeros((h, w), np.uint8)
            bg = np.zeros((1, 65), np.float64)
            fg = np.zeros((1, 65), np.float64)
            # Kenarlardan %5 iceri al
            mx, my = max(2, int(w * 0.05)), max(2, int(h * 0.05))
            rect = (mx, my, w - 2 * mx, h - 2 * my)
            cv2.grabCut(image, mask, rect, bg, fg, 5, cv2.GC_INIT_WITH_RECT)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
            result = image.copy()
            result[mask2 == 0] = [255, 255, 255]  # arka plani beyaz yap
            print('Arka plan basariyla silindi (beyaza cevrildi)')
            return result
        except Exception as e:
            print(f'Arka plan silme hatasi: {e}')
            return image

    def _stretch_to_standard(self, image):
        """Goruntuyu TC kimlik kartinin standart boyutlarina esneterek kirpar.
        Standart boyut: 856 x 540 px (85.6mm x 53.98mm oraninda)"""
        STD_W, STD_H = 856, 540
        h, w = image.shape[:2] if len(image.shape) == 3 else (image.shape[0], image.shape[1])
        if w < h:  # dikey ise yataya cevir
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        stretched = cv2.resize(image, (STD_W, STD_H), interpolation=cv2.INTER_LANCZOS4)
        print(f'Standart boyuta esnetildi: {STD_W}x{STD_H}')
        return stretched

    def smart_crop(self, image):
        """Akilli kirpma pipeline'i: algi -> kirp -> arka plan sil -> esneterek boyutlandir"""
        if not self.auto_crop_var.get():
            # Kirpma kapali olsa bile dikey ise yataya cevir ve esneterek boyutlandir
            return self._stretch_to_standard(image)

        # 1) Kontur tabanli algilama
        bounds = self.detect_id_card(image)
        if bounds is not None:
            x, y, w, h = bounds
            margin = int(self.margin_var.get())
            oh, ow = image.shape[:2]
            x0 = max(0, x - margin)
            y0 = max(0, y - margin)
            x1 = min(ow, x + w + margin)
            y1 = min(oh, y + h + margin)
            cropped = image[y0:y1, x0:x1]
            print(f'Kimlik algilandi ve kirpildi: {x1-x0}x{y1-y0}')
            cropped = self._remove_background(cropped)
            return self._stretch_to_standard(cropped)

        # 2) Perspektif duzeltme
        print('Kontur algilama basarisiz, perspektif deneniyor...')
        persp = self._perspective_crop(image)
        if persp is not None:
            persp = self._remove_background(persp)
            return self._stretch_to_standard(persp)

        # 3) Merkezi kirpma (son care)
        print('Perspektif de basarisiz, merkezi kirpma...')
        return self._center_crop(image)

    def _center_crop(self, image):
        h, w = image.shape[:2]
        if w < h:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
            h, w = image.shape[:2]
        target = 1.586
        cur = w / h
        if cur > target:
            nw = int(h * target)
            sx = (w - nw) // 2
            image = image[0:h, sx:sx + nw]
        else:
            nh = int(w / target)
            sy = (h - nh) // 2
            image = image[sy:sy + nh, 0:w]
        return self._stretch_to_standard(image)

    # ------------------------------------------------------------------
    # GORUNTU IYILESTIRME (siyah-beyaz)
    # ------------------------------------------------------------------
    def enhance_image(self, image):
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        q = int(self.quality_var.get())
        dn_h = max(3, min(15, q // 8))
        dn = cv2.fastNlMeansDenoising(gray, None, h=dn_h, templateWindowSize=7,
                                       searchWindowSize=21)
        cl = 1.5 + (q / 100.0) * 1.5
        clahe = cv2.createCLAHE(clipLimit=cl, tileGridSize=(8, 8))
        enh = clahe.apply(dn)

        if q > 30:
            sa = 0.1 + (q / 100.0) * 0.3
            kern = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
            sh = cv2.filter2D(enh, -1, kern)
            enh = cv2.addWeighted(enh, 1.0 - sa, sh, sa, 0)

        print(f'S/B donusum tamamlandi (iyilestirme: %{q})')
        return enh

    # ------------------------------------------------------------------
    # ISLEM HATTI
    # ------------------------------------------------------------------
    def process_image(self, path, suffix):
        image = imread_unicode(path)
        if image is None:
            raise ValueError('Goruntu yuklenemedi')

        print(f"\n{'='*50}\nIsleniyor: {suffix}")
        print(f'Orijinal: {image.shape[1]}x{image.shape[0]}')

        self.update_status(30, f'{suffix.capitalize()} y\u00fcz k\u0131rp\u0131l\u0131yor...')
        cropped = self.smart_crop(image)

        self.update_status(60, 'S/B d\u00f6n\u00fc\u015f\u00fcm...')
        enhanced = self.enhance_image(cropped)

        # Son dikey kontrol
        eh, ew = (enhanced.shape[:2] if len(enhanced.shape) == 3
                  else (enhanced.shape[0], enhanced.shape[1]))
        if ew < eh:
            enhanced = cv2.rotate(enhanced, cv2.ROTATE_90_COUNTERCLOCKWISE)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        tmp = os.path.join(self.temp_dir, f'_tmp_{suffix}_{ts}.png')
        os.makedirs(self.temp_dir, exist_ok=True)
        if not imwrite_unicode(tmp, enhanced):
            raise ValueError('Gecici dosya olusturulamadi')
        print(f'Gecici: {tmp} ({os.path.getsize(tmp)} byte)\n{"="*50}')
        return tmp

    def start_processing(self):
        if not self.front_image_path and not self.back_image_path:
            messagebox.showwarning('Uyar\u0131', 'L\u00fctfen en az bir g\u00f6rsel se\u00e7in!')
            return
        self._toggle_btns('disabled')
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        temps = []
        try:
            self.progress_var.set(0)
            self.update_status(10, '\u0130\u015flem ba\u015flat\u0131l\u0131yor...')
            os.makedirs(self.output_dir, exist_ok=True)

            if self.front_image_path:
                self.update_status(20, '\u00d6n y\u00fcz i\u015fleniyor...')
                temps.append(self.process_image(self.front_image_path, 'on'))
                self.progress_var.set(40)

            if self.back_image_path:
                self.update_status(50, 'Arka y\u00fcz i\u015fleniyor...')
                temps.append(self.process_image(self.back_image_path, 'arka'))
                self.progress_var.set(70)

            pdf = None
            if temps:
                self.update_status(80, 'PDF olu\u015fturuluyor...')
                pdf = self._make_pdf(temps)
                self.progress_var.set(95)

            for t in temps:
                try: os.remove(t)
                except: pass

            self.update_status(100, '\u0130\u015flem tamamland\u0131!')
            if pdf:
                sz = os.path.getsize(pdf) / 1024
                n = len(temps)
                yt = '\u00f6n + arka y\u00fcz' if n == 2 else 'tek y\u00fcz'
                messagebox.showinfo('Ba\u015far\u0131l\u0131',
                    f'\u0130\u015flem tamamland\u0131!\n\n'
                    f'PDF: {os.path.basename(pdf)}\n'
                    f'Boyut: {sz:.1f} KB ({yt})\n'
                    f'Kart \u00f6l\u00e7e\u011fi: %{self.pdf_scale_var.get()}\n\n'
                    f'Kay\u0131t konumunu kopyalamak i\u00e7in\n'
                    f'Kay\u0131t Bilgisi alan\u0131ndaki yola t\u0131klay\u0131n.')
            self.progress_var.set(0)

        except Exception as e:
            for t in temps:
                try: os.remove(t)
                except: pass
            messagebox.showerror('\u0130\u015flem Hatas\u0131', str(e))
            self.update_status(0, f'Hata: {e}')
            self.progress_var.set(0)
        finally:
            self._toggle_btns('normal')

    # ------------------------------------------------------------------
    # PDF OLUSTURMA
    # ------------------------------------------------------------------
    def _make_pdf(self, paths):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(self.output_dir, f'kimlik_{ts}.pdf')

        imgs = []
        for p in paths:
            im = Image.open(p)
            if im.mode != 'RGB':
                im = im.convert('RGB')
            if im.width < im.height:
                im = im.transpose(Image.ROTATE_90)
            imgs.append(im.copy())
            im.close()

        if not imgs:
            raise ValueError('PDF icin goruntu yok')

        scale = self.pdf_scale_var.get() / 100.0
        dpi = 150
        pw, ph = int(8.27 * dpi), int(11.69 * dpi)
        mg = int(0.5 * dpi)
        full_w = pw - 2 * mg
        usable_w = int(full_w * scale)
        spacing = int(0.3 * dpi)
        avail_h = ph - 2 * mg
        each_h = (avail_h - spacing * (len(imgs) - 1)) // len(imgs)

        page = Image.new('RGB', (pw, ph), (255, 255, 255))
        y = mg
        for im in imgs:
            r = im.width / im.height
            tw, th = usable_w, int(usable_w / r)
            if th > each_h:
                th = each_h
                tw = int(th * r)
            resized = im.resize((tw, th), Image.LANCZOS)
            x = mg + (full_w - tw) // 2
            page.paste(resized, (x, y))
            y += th + spacing

        page.save(pdf_path, format='PDF', resolution=dpi)
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise ValueError('PDF olusturulamadi')
        self.last_pdf_path = pdf_path
        print(f'PDF olusturuldu: {pdf_path} ({os.path.getsize(pdf_path)} byte)')
        return pdf_path

    # ------------------------------------------------------------------
    # YAZDIR / KLASOR / CIKIS
    # ------------------------------------------------------------------
    def print_pdf(self):
        try:
            if not self.last_pdf_path or not os.path.exists(self.last_pdf_path):
                messagebox.showwarning('Uyar\u0131',
                    'Yazd\u0131r\u0131lacak PDF yok.\n\u00d6nce i\u015flemi ba\u015flat\u0131n.')
                return
            p = os.path.normpath(self.last_pdf_path)
            s = platform.system()
            if s == 'Windows':
                os.startfile(p)
            elif s == 'Darwin':
                subprocess.Popen(['open', p])
            else:
                subprocess.Popen(['xdg-open', p])
            self.update_status(0, 'PDF a\u00e7\u0131ld\u0131 \u2013 Ctrl+P ile yazd\u0131r\u0131n')
        except Exception as e:
            messagebox.showerror('Hata', f'PDF a\u00e7\u0131lamad\u0131:\n{e}')

    def open_output_folder(self):
        try:
            if os.path.exists(self.output_dir):
                if platform.system() == 'Windows':
                    os.startfile(self.output_dir)
                elif platform.system() == 'Darwin':
                    subprocess.Popen(['open', self.output_dir])
                else:
                    subprocess.Popen(['xdg-open', self.output_dir])
            else:
                messagebox.showinfo('Bilgi', f'Klas\u00f6r hen\u00fcz olu\u015fturulmad\u0131.')
        except Exception as e:
            messagebox.showerror('Hata', str(e))

    def _toggle_btns(self, state):
        for child in self.root.winfo_children():
            self._recursive_btn_state(child, state)

    def _recursive_btn_state(self, widget, state):
        if isinstance(widget, ttk.Button):
            widget.config(state=state)
        for child in widget.winfo_children():
            self._recursive_btn_state(child, state)

    def cleanup_and_exit(self):
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass
        self.root.quit()

    def run(self):
        self.root.protocol('WM_DELETE_WINDOW', self.cleanup_and_exit)
        self.root.mainloop()


if __name__ == '__main__':
    print('TC Kimlik Karti Duzenleyici v2 by SWAPNIL')
    print('=' * 60)
    print('Ozellikler:')
    print('  Akilli kimlik karti algilama + kirpma + esnetme')
    print('  Perspektif duzeltme (egik fotolar)')
    print('  Arka plan silme (GrabCut)')
    print('  Siyah-beyaz donusum + iyilestirme')
    print('  PDF cikti (ayarlanabilir kart boyutu)')
    print('  Turkce karakter destegi')
    print('  Tek tikla yazdirma')
    print('=' * 60)
    app = IDCardProcessor()
    app.run()
