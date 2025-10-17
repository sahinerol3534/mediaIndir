# mp3-mp4-indir1.pyw
import os
import sys
import json
import threading
import subprocess
import urllib.request
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import shutil
from tkinter import PhotoImage
import platform

# ---------- Helper: AppData paths & logging ----------
APP_NAME = "MP3MP4_Indirici"

def get_appdata_dir(*subdirs):
    # Cross-platform AppData alternative: Windows -> %APPDATA%, else -> ~/.config
    if os.name == "nt":
        base_root = os.getenv("APPDATA") or os.path.expanduser("~")
    else:
        base_root = os.path.expanduser("~/.config")
    base = os.path.join(base_root, APP_NAME, *subdirs)
    os.makedirs(base, exist_ok=True)
    return base

def get_config_path():
    return os.path.join(get_appdata_dir(), "config.txt")

def write_log(text):
    try:
        log_dir = get_appdata_dir("logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "last.log")
        ts = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {text}\n")
    except Exception:
        pass

def show_message(title, text, icon=0):
    # Windows: use MessageBoxW as before; else fallback to tkinter messagebox
    try:
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(0, text, title, icon)
        else:
            # Non-blocking console fallback + tkinter info if possible
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo(title, text)
                root.destroy()
            except Exception:
                print(f"[{title}] {text}")
    except Exception:
        # Last resort
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(title, text)
            root.destroy()
        except Exception:
            print(f"[{title}] {text}")

# ---------- ffmpeg check ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_DIR = os.path.join(BASE_DIR, "ffmpeg", "bin")

def ensure_ffmpeg(status_callback=None):
    """
    ffmpeg mevcut değilse mp3Mp4-indir/ffmpeg/bin dizinine indir.
    Platformlar arası davranış:
    - Eğer sistemde PATH'de ffmpeg varsa onu kullan -> return dizin
    - Eğer daha önce indirilmişse mp3Mp4-indir/ffmpeg içinde tara ve return et
    - İndirilemiyorsa hata logla ama programı kapatma; return olası FFMPEG_DIR (çalışma dizini)
    """
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"

    # 0) PATH'de var mı?
    which = shutil.which(exe_name)
    if which:
        ff_dir = os.path.dirname(os.path.abspath(which))
        write_log(f"ffmpeg PATH'te bulundu -> {ff_dir}")
        return ff_dir

    # 1) Tarama: FFMPEG_DIR ve alt klasörler
    if os.path.exists(FFMPEG_DIR):
        for root, dirs, files in os.walk(os.path.dirname(FFMPEG_DIR)):
            if exe_name in files:
                write_log(f"ffmpeg bulundu -> {root}")
                return root

    # 2) Eğer daha önce indirilmeye çalışıldıysa ve exe yoksa önce hiçbir şey indirmeden FFMPEG_DIR'i döndürme mantığı:
    # -- ama kullanıcı daha önceden indirmiş olabilir başka dizine; yukarıdaki tarama bunun için yeterli.

    # 3) İndir (yalnızca Windows için zip url, Linux/mac için farklı url)
    os.makedirs(FFMPEG_DIR, exist_ok=True)
    if status_callback:
        status_callback("ffmpeg kontrol ediliyor... (indirilmeye çalışılacak ise bildirilecektir)")

    # choose URL by platform
    if platform.system() == "Windows":
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        tmp_archive = os.path.join(FFMPEG_DIR, "ffmpeg.zip")
        try:
            if status_callback:
                status_callback("ffmpeg indiriliyor...")
            urllib.request.urlretrieve(url, tmp_archive)
            if status_callback:
                status_callback("ffmpeg indirildi, açılıyor...")
            import zipfile
            with zipfile.ZipFile(tmp_archive, 'r') as zip_ref:
                # extract into ffmpeg parent so structure will be ffmpeg/<folder>/
                zip_ref.extractall(os.path.dirname(FFMPEG_DIR))
            try:
                os.remove(tmp_archive)
            except Exception:
                pass
            # tekrar tara
            for root, dirs, files in os.walk(os.path.dirname(FFMPEG_DIR)):
                if exe_name in files:
                    write_log(f"ffmpeg kuruldu -> {root}")
                    return root
            write_log("ffmpeg indirildi ama exe bulunamadı!")
            show_message("Hata", "ffmpeg indirildi ama çalıştırılabilir dosya bulunamadı!")
            return FFMPEG_DIR
        except Exception as e:
            write_log(f"ffmpeg indirilemedi: {e}")
            show_message("Hata", f"ffmpeg indirilemedi: {e}")
            # indirme başarısız olsa bile FFMPEG_DIR'i döndür (program mp4 indirmeye çalışabilir)
            return FFMPEG_DIR
    else:
        # Linux / macOS: dene statik tarball
        # Not: bazı sistemlerde manual kurulum gerekebilir. Burada basitçe tarball indirme denemesi var.
        if platform.system() == "Darwin":
            # macOS: genellikle brew ile kurulur; biz indirmeye çalışmıyoruz otomatik
            write_log("macOS: PATH içinde ffmpeg kontrol edildi. Otomatik indirme yok.")
            return FFMPEG_DIR
        else:
            # Linux
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            tmp_archive = os.path.join(FFMPEG_DIR, "ffmpeg.tar.xz")
            try:
                if status_callback:
                    status_callback("ffmpeg indiriliyor...")
                urllib.request.urlretrieve(url, tmp_archive)
                if status_callback:
                    status_callback("ffmpeg indirildi, açılıyor...")
                # extract with tar via subprocess to TOOLS dir
                parent = os.path.dirname(FFMPEG_DIR)
                os.makedirs(parent, exist_ok=True)
                subprocess.run(["tar", "xf", tmp_archive, "-C", parent], check=True)
                try:
                    os.remove(tmp_archive)
                except Exception:
                    pass
                for root, dirs, files in os.walk(parent):
                    if exe_name in files:
                        write_log(f"ffmpeg kuruldu -> {root}")
                        return root
                write_log("ffmpeg indirildi ama exe bulunamadı!")
                return FFMPEG_DIR
            except Exception as e:
                write_log(f"ffmpeg indirilemedi: {e}")
                show_message("Hata", f"ffmpeg indirilemedi: {e}")
                return FFMPEG_DIR

# ---------- Locate or download yt-dlp ----------
def find_ytdlp():
    candidates = []
    meipass = getattr(sys, '_MEIPASS', None)
    exe_name = "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
    if meipass:
        candidates.append(os.path.join(meipass, exe_name))
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, exe_name))
    try:
        script_dir = os.path.dirname(__file__)
        candidates.append(os.path.join(script_dir, exe_name))
    except NameError:
        pass
    candidates.append(os.path.join(os.getcwd(), exe_name))
    candidates.append(os.path.join(get_appdata_dir("program_files"), exe_name))
    which = shutil.which("yt-dlp") or shutil.which(exe_name)
    if which:
        candidates.append(which)
    seen = set()
    for c in candidates:
        if not c:
            continue
        c = os.path.abspath(c)
        if c in seen:
            continue
        seen.add(c)
        if os.path.exists(c):
            return c
    return None

def download_ytdlp_to_appdata(status_callback=None):
    target_dir = get_appdata_dir("program_files")
    os.makedirs(target_dir, exist_ok=True)
    exe_name = "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
    target_path = os.path.join(target_dir, exe_name)
    url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" if os.name == "nt" else "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
    try:
        if status_callback:
            status_callback("yt-dlp indiriliyor...")
        def progress(block_num, block_size, total_size):
            if total_size > 0:
                percent = min(100, (block_num * block_size * 100) // total_size)
                if status_callback:
                    status_callback(f"yt-dlp indiriliyor... %{percent}")
        urllib.request.urlretrieve(url, target_path, progress)
        try:
            os.chmod(target_path, 0o755)
        except Exception:
            pass
        if status_callback:
            status_callback("yt-dlp indirildi ✓")
        write_log(f"yt-dlp indirildi -> {target_path}")
        return target_path
    except Exception as e:
        write_log(f"yt-dlp indirilemedi: {e}")
        return None

def ensure_ytdlp(status_callback=None, allow_download=True):
    p = find_ytdlp()
    if p:
        write_log(f"yt-dlp bulundu: {p}")
        return p
    if allow_download:
        p = download_ytdlp_to_appdata(status_callback=status_callback)
        if p:
            return p
    return None

# ---------- GUI setup ----------
def klasor_sec_initial():
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Kurulum", "İlk kullanım: indirme klasörünü seçin.")
    selected = filedialog.askdirectory(title="Ana İndirme Klasörünü Seç")
    if not selected:
        messagebox.showwarning("İptal", "Herhangi bir klasör seçilmedi. Program kapanacak.")
        sys.exit(0)
    with open(get_config_path(), "w", encoding="utf-8") as f:
        f.write(selected)
    root.destroy()
    return selected

def klasor_yukle():
    path = get_config_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            p = f.read().strip()
            if os.path.exists(p):
                return p
    return klasor_sec_initial()

# ---------- Main GUI app ----------
class MP3MP4App:
    def _fix_facebook_url(self, url: str) -> str:
        try:
            if "facebook.com/watch" in url and "v=" in url:
                import urllib.parse as up
                parsed = up.urlparse(url)
                params = up.parse_qs(parsed.query)
                video_id = params.get("v", [None])[0]
                if video_id:
                    fixed_url = f"https://www.facebook.com/video.php?v={video_id}"
                    self._set_status("Facebook bağlantısı dönüştürüldü ✅")
                    return fixed_url
            return url
        except Exception as e:
            self._set_status(f"Facebook URL dönüştürme hatası: {e}")
            return url

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(False)
        self.width = 600
        self.height = 300
        self.root.title("MediaIndirici")
        self.root.geometry("600x300+300+300")
        self.root.configure(bg="#24315C")
        self.root.resizable(False, False)
        self.ANA_KLASOR = klasor_yukle()
        self._build_ui()
        # initial checks after UI built so status_label exists
        self.root.after(150, self._initial_ytdlp_check)
        self.root.mainloop()

    def _build_ui(self):
        tk.Label(self.root, text="MediaIndirici AUDIO/VIDEO", bg="#24315C", fg="#00ff88",
                 font=("Segoe UI", 16, "bold italic")).pack(pady=30)
        self.status_label = tk.Label(self.root, text="Hazır", bg="#24315C", fg="#00ff88")
        self.status_label.pack(pady=4)

        url_frame = tk.Frame(self.root, bg="#24315C")
        url_frame.pack(pady=(10,6))
        tk.Label(url_frame, text="URL: ", width=7, bg="#24315C", fg="#00ff88",
                 font = ("Segeo UI", 10)).grid(row = 0, column = 0, sticky="w", padx = 0)
        self.url_entry = tk.Entry(url_frame, width=68, bg="#69A1CC", fg="#24315C", font=("Segoe UI", 10))
        self.url_entry.grid(row = 0, column = 1, sticky="w", padx = 0)

        frame = tk.Frame(self.root, bg="#24315C")
        frame.pack(pady=(12,6))
        tk.Label(frame, text="Ana Klasör:", bg="#24315C", fg="#00ff88").grid(row=0, column=0, sticky="w")
        self.klasor_label = tk.Label(frame, text=self.ANA_KLASOR, bg="#69A1CC", fg="#24315C",
                                     width=50, anchor="w", relief="sunken")
        self.klasor_label.grid(row=0, column=1, padx=7)
        tk.Button(frame, text=" Klasör Değiştir ", command=self.klasor_degistir,
                  bg="#69A1CC", fg="#032EBB", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=7)

        btn_frame = tk.Frame(self.root, bg="#24315C")
        btn_frame.pack(pady=6)
        tk.Label(btn_frame, width=9, bg="#24315C").grid(row=0, column=0, sticky="w")
        tk.Button(btn_frame, text="MP3 İndir", width=21, command=lambda: self.indir("mp3"),
                  bg="#69A1CC", fg="#032EBB", font=("Segoe UI", 8, "bold")).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="MP4 İndir", width=21, command=lambda: self.indir("mp4"),
                  bg="#69A1CC", fg="#032EBB", font=("Segoe UI", 8, "bold")).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Temizle", width=20, command=self.temizle,
                  bg="#69A1CC", fg="#032EBB", font=("Segoe UI", 8, "bold")).grid(row=0, column=3, padx=3)
        tk.Label(self.root, text="Şahin EROL", bg="#24315C", fg="#00ff88",
                 font=("Segoe UI", 6, "bold italic")).pack(pady=(20,2),padx=(500,6))

    def klasor_degistir(self):
        yeni = filedialog.askdirectory(title="Ana İndirme Klasörünü Seç", initialdir=self.ANA_KLASOR)
        if yeni:
            self.ANA_KLASOR = yeni
            self.klasor_label.config(text=self.ANA_KLASOR)
            with open(get_config_path(), "w", encoding="utf-8") as f:
                f.write(self.ANA_KLASOR)
            self.status_label.config(text="Ana klasör güncellendi")

    def temizle(self):
        self.url_entry.delete(0, tk.END)
        self.status_label.config(text="Hazır")

    def _initial_ytdlp_check(self):
        self.status_label.config(text="yt-dlp kontrol ediliyor...")
        p = ensure_ytdlp(status_callback=lambda t: self._set_status(t), allow_download=True)
        if p:
            self._set_status("Hazır ---> URL girin")
        else:
            self._set_status("❌ yt-dlp bulunamadı")

    def _set_status(self, text):
        # thread-safe status update
        try:
            self.root.after(0, lambda: self.status_label.config(text=text))
        except Exception:
            pass

    def indir(self, format_turu):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Hata", "Lütfen bir URL girin.")
            return

        def worker():
            try:
                self._set_status("İndirme başlatılıyor...")
                ytdlp_path = ensure_ytdlp(status_callback=lambda t: self._set_status(t), allow_download=True)
                ffmpeg_path = ensure_ffmpeg(status_callback=lambda t: self._set_status(t))  # always returns a path (maybe intended dir)

                if not ytdlp_path:
                    self._set_status("❌ yt-dlp bulunamadı!")
                    messagebox.showerror("Hata", "yt-dlp bulunamadı ve indirilemedi, bazı işlemler başarısız olabilir.")
                    return

                exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
                ffmpeg_ok = False
                if ffmpeg_path and os.path.exists(os.path.join(ffmpeg_path, exe_name)):
                    ffmpeg_ok = True
                else:
                    # also check PATH as fallback (for systems where ensure_ffmpeg returned folder but exe in PATH)
                    if shutil.which(exe_name):
                        ffmpeg_ok = True

                if not ffmpeg_ok and format_turu == "mp3":
                    self._set_status("⚠️ ffmpeg bulunamadı! MP3 dönüştürme başarısız olabilir.")
                    write_log("ffmpeg bulunamadı, mp3 dönüştürme hataları olabilir.")

                hedef = os.path.join(self.ANA_KLASOR, datetime.now().strftime("indirmeler_%d-%m-%Y_%H-%M-%S"))
                os.makedirs(hedef, exist_ok=True)

                if format_turu == "mp3":
                    cmd = [
                        ytdlp_path,
                        "-x",
                        "--audio-format", "mp3",
                        "--audio-quality", "0",
                        "--ffmpeg-location", ffmpeg_path,
                        "--cookies", "cookies.txt",
                        "-o", os.path.join(hedef, "%(title).80s.%(ext)s"),
                        url
                    ]
                else:
                    cmd = [
                        ytdlp_path,
                        "-f", "bestvideo+bestaudio/best",
                        "--merge-output-format", "mp4",
                        "--ffmpeg-location", ffmpeg_path,
                        "--cookies", "cookies.txt",
                        "-o", os.path.join(hedef, "%(title).80s.%(ext)s"),
                        url
                    ]

                write_log(f"Başlatılan komut: {' '.join(cmd)}")
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                startupinfo = None
                if os.name == "nt":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )

                last_filename = None
                # parse yt-dlp output and update status_label (preserve previous parsing logic)
                for raw in iter(proc.stdout.readline, ''):
                    if raw is None:
                        break
                    line = raw.strip()
                    if not line:
                        continue
                    write_log(line)
                    if "Destination:" in line:
                        last_filename = line.split("Destination:",1)[1].strip().strip('"')
                        self._set_status(f"Dosya: {os.path.basename(last_filename)}")
                    elif "Merging formats into" in line or "Merging" in line:
                        import re
                        m = re.search(r'"([^"]+\.(?:mp4|mkv|webm|m4a|mp3))"', line)
                        if m:
                            last_filename = m.group(1)
                        if last_filename:
                            self._set_status(f"Media Düzenleniyor! {os.path.basename(last_filename)}")
                    elif "%" in line:
                        import re
                        m = re.search(r'(\d{1,3}(?:\.\d+)?)%', line)
                        if m:
                            self._set_status(f"İndiriliyor: {m.group(1)}%")

                proc.wait()
                rc = proc.returncode
                write_log(f"yt-dlp dönüş kodu: {rc}")
                if rc == 0:
                    if last_filename:
                        msg = f"İndirme tamamlandı: {os.path.basename(last_filename)}"
                    else:
                        msg = "İndirme tamamlandı!"
                    write_log(msg)
                    self._set_status("✅ İndirme tamamlandı")
                    try:
                        import winsound
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    except Exception:
                        pass
                    messagebox.showinfo("Başarılı", f"{msg}\n\nKlasör: {hedef}")
                else:
                    raise Exception(f"yt-dlp hata kodu: {rc}. Log'a bakın.")

            except Exception as e:
                write_log(f"İndirme hatası: {e}")
                self._set_status("❌ İndirme başarısız")
                messagebox.showerror("Hata", f"İndirme hatası: {e}")

        threading.Thread(target=worker, daemon=True).start()

# ---------- Yasal uyarı ----------
def show_yasal_uyari():
    # Bu pencere modal olacak; kullanıcı KABUL ETMEDEN program başlamayacak.
    win = tk.Tk()
    win.title("Yasal Uyarı")
    win.geometry("750x340+400+250")
    win.configure(bg="#24315C")
    # disable resizing to preserve look
    win.resizable(False, False)

    msg_title =("⚠️ YASAL UYARI ⚠️")
    msg = ("MediaIndir, sadece kullanıcının erişim izni olan ve/veya telifsiz video ve/veya ses dosyalarının indirilmesi amacıyla geliştirilmiştir.\n\n"
           "- Telif haklarıyla korunan içeriklerin indirilmesi yasalara aykırıdır ve içerik sahibininhaklarını ihlal eder.\n\n"
           "- MediaIndir geliştiricisi, programın telif haklarıının ihlali yapan kullanımlar nedeniyle oluşacak yasal sorumluluklardan sorumlu tutulamaz.\n\n"
           "- Kullanıcı, bu yazılımı kullanarak oluşabilecek her türlü yasal sorumluluğu kabul etmiş sayılır." )
    msg_tail = ("***** Lütfen sadece KİŞİSEL kullanım ve EĞİTİM amaçlı içerikleri indirin *****")

    tk.Label(win, text=msg_title, wraplength=480, justify="center", bg="white", fg="#ff0000",
             font=("Segoe UI", 10, "bold")).pack(pady=(30,2))
    tk.Label(win, text=msg, wraplength=730, justify="left", bg="#24315C", fg="#00ff88",
             font=("Segoe UI", 8)).pack(pady=(30,2))
    tk.Label(win, text=msg_tail, wraplength=480, justify="center", bg="#E0E4F0", fg="#ff0000",
             font=("Segoe UI", 10)).pack(pady=(30,2))

    def kabul_et():
        # kullanıcı kabul ederse modal kapat ve program başlasın
        win.grab_release()
        win.destroy()
        MP3MP4App()

    def reddet():
        # reddederse açıkça çık
        try:
            messagebox.showinfo("Kapatılıyor", "Yasal uyarı reddedildi. Program kapatılıyor.")
        except Exception:
            print("Yasal uyarı reddedildi. Program kapatılıyor.")
        win.grab_release()
        win.destroy()
        sys.exit(0)

    # buttons
    btn_frame = tk.Frame(win, bg="#24315C")
    btn_frame.pack(pady=20)
    tk.Button(btn_frame, text="KABUL EDİYORUM", width=18, command=kabul_et, bg="green", fg="white").grid(row=0, column=0, padx=10)
    tk.Button(btn_frame, text="REDEDİYORUM", width=18, command=reddet, bg="red", fg="white").grid(row=0, column=1, padx=10)

    # make modal: prevent interacting with other windows and block until closed
    win.protocol("WM_DELETE_WINDOW", reddet)  # pencere kapama = reddet
    win.lift()
    win.attributes("-topmost", True)
    win.grab_set()
    win.mainloop()

if __name__ == "__main__":
    show_yasal_uyari()
