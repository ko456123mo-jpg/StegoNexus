# 🖥️ دليل تشغيل StegoNexus على جهازك (Kali Linux)

> المشروع مرفوع على GitHub: **https://github.com/ko456123mo-jpg/StegoNexus** (خاص)
> — إعداد: Mohammed Moneer Al-absi

---

## 0) المتطلبات

| المتطلب | التفاصيل |
|---|---|
| نظام تشغيل | Kali Linux 2023+ (يعمل أيضاً على Debian/Ubuntu) |
| Python | 3.9 أو أحدث (`python3 --version`) |
| git | `sudo apt install git` |
| إنترنت | لتنزيل الحزم وصور الأدوات |

---

## 1) الحصول على المشروع (طريقتان)

### الطريقة أ — git clone (الأفضل للتحديثات)
```bash
cd ~
git clone https://github.com/ko456123mo-jpg/StegoNexus.git
cd StegoNexus
```
> المستودع **خاص** → سيطلب اسم المستخدم + **توكن** بدل كلمة المرور.
> (أنشئ توكن قصير العمر من Settings → Developer settings → Tokens (classic)
> بصلاحية `repo`، ثم أبطله بعد الاستنساخ)

### الطريقة ب — تنزيل ZIP (بدون توكن — الأسهل)
1. افتح رابط المستودع في المتصفح
2. زر **Code ▼** → **Download ZIP**
3. فك الضغط:
```bash
unzip StegoNexus-main.zip && cd StegoNexus-main
```

---

## 2) تثبيت المتطلبات

### 2.1 أدوات Kali الخارجية (مطلوبة للوضع الكامل — اختيارية لأن البدائل مدمجة)
```bash
sudo apt update
sudo apt install -y steghide exiftool binwalk foremost ffmpeg
# zsteg يعتمد على Ruby:
sudo gem install zsteg
```
> عند غياب أي أداة، StegoNexus يعمل تلقائياً ببدائله المدمجة (يظهر ذلك في
> Dashboard → جدول "Status/Fallback").

### 2.2 حزم Python (يُفضَّل داخل بيئة معزولة)
```bash
sudo apt install -y python3-venv python3-pip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt        # numpy, Pillow, PySide6, pycryptodome
```
> إذا ظهرت رسالة `externally-managed-environment` (Kali 2024+)، يستخدم النظام
> الـ venv أعلاه. وللتثبيت الكلي يمكن: `pip install --break-system-packages -r requirements.txt`

### 2.3 (إن رغبت) تثبيت المشروع كحزمة — يتيح أمر `stegonexus` و `stegonexus-gui`
```bash
pip install -e .
```

---

## 3) التشغيل

### 3.1 الواجهة الرسومية (Dashboard) ⭐ الأسهل للتجربة
```bash
python run_gui.py
# أو بعد التثبيت كحزمة:
stegonexus-gui
```
ستظهر لوحة تحكم داكنة فيها 10 صفحات:
`Dashboard · Forensics & Analysis · Hashing · Text LSB · Image · Audio ·
Video · Network · Malware Lab · Case Management`

> **بدون واجهة رسومية (سيرفر/VM فقط):** جرّب بالبيئة الوهمية
> `QT_QPA_PLATFORM=offscreen python run_gui.py` (ستعمل لكن دون عرض).

### 3.2 خط الأوامر (CLI)
```bash
python run_cli.py --help        # كل الأوامر المتاحة

# Hashing
python run_cli.py hash server.iso -a MD5 SHA-256

# Text LSB + Key
python run_cli.py text hide cover.txt --message secret.txt --key "MyKey" --output stego.txt
python run_cli.py text reveal stego.txt --key "MyKey"

# Image — Steghide (JPEG) أو CyberHide تلقائياً
python run_cli.py image photo.jpg secret.bin --password "pw"
python run_cli.py image-unhide photo_stego.jpg --password "pw"
python run_cli.py image-info photo_stego.jpg --password "pw"

# Audio — 4 طرق
python run_cli.py audio lsb   song.wav secret.bin --key "ak"
python run_cli.py audio phase song.wav secret.bin --key "pk"
python run_cli.py audio ss    song.wav secret.bin --key "sk"
python run_cli.py audio meta  song.wav secret.bin --key "mk"
python run_cli.py audio-unhide lsb song_stego.wav --key "ak"
python run_cli.py audio-analyze song.wav && python run_cli.py spectrogram song.wav

# Video — يحتاج ffmpeg
python run_cli.py video-info cover.mp4
python run_cli.py video cover.mp4 secret.bin --key "vk"
python run_cli.py video-unhide cover_vstego.mkv --key "vk"

# Network — 3 قنوات خفية
python run_cli.py network secret.bin --key "nk" --mode ipid --output covert.pcap
python run_cli.py network-detect covert.pcap
python run_cli.py network-unhide covert.pcap --key "nk" --mode ipid

# Malware Lab
python run_cli.py malware sample.exe
python run_cli.py demo-stub --output stub.py

# Forensics (كل الأدوات في تقرير واحد)
python run_cli.py forensics suspicious.jpg
python run_cli.py forensics stego.jpg --password "pw"   # مع كلمة مرور steghide

# Case Management
python run_cli.py case create --title "تحقيق 1" --examiner "أنا"
python run_cli.py case list
python run_cli.py case export --case-id CASE-XXXX --format md
```

### 3.3 تشغيل العرض الشامل (كل الأقسام دفعة واحدة)
```bash
python demo.py
```
ينتج كل شيء داخل `demo_output/` (صور stego، صوت بكل الطرق، فيديو، ملفات pcap،
قضية Case بتقارير MD/JSON/HTML، spectrogram…).

---

## 4) التحقق من سلامة النسخة على جهازك
```bash
python tests/test_integration.py     # 24/24 = كل الوحدات تعمل
python tests/test_requirements.py    # 60/60 = كل بنود المتطلبات (فحوصات حية)
```

---

## 5) حل المشاكل الشائعة

| المشكلة | الحل |
|---|---|
| `ImportError: libxkbcommon.so.0` أو `libGL` عند تشغيل الواجهة | `sudo apt install -y libxkbcommon0 libgl1 libegl1 libfontconfig1` |
| `externally-managed-environment` عند pip | استخدم الـ venv (الخطوة 2.2) |
| `steghide: the file format ... is not supported` | steghide يدعم JPEG/BMP فقط → استخدم صورة JPEG (أو PNG فيوضع CyberHide تلقائياً) |
| `zsteg: command not found` | `sudo gem install zsteg` (ثبّت ruby أولاً: `sudo apt install ruby`) |
| رسالة نص الغلاف قصير (Text LSB) | كل بايت سري يحتاج ~64 حرف حامل (ترويسة+تشفير) → أطِل النص الحامل |
| Spread Spectrum فشل الاستخراج | استخدم مقطعاً هادئاً (إشارة منخفضة) — موثق في الكود |
| Video: لا يوجد ffmpeg | `sudo apt install -y ffmpeg` (وبدونه تعمل Container Hiding فقط) |
| الملفات لا تظهر بعد التنزيل ZIP | بعض الأنظمة "تُخفي" الصور المولّدة في المجلدات الفرعية — اسمح بالعرض المخفي/انزل لمجلد demo_output |
| نافذة فارغة عند تشغيل GUI | جرّب `QT_QPA_PLATFORM=xcb python run_gui.py` أو أعد تسجيل الدخول بالجلسة الرسومية |

---

## 6) خريطة المجلدات (ماذا ينظر إلى أين)

```
StegoNexus/
├── run_gui.py / run_cli.py        ← نقاط التشغيل
├── demo.py                        ← عرض شامل
├── stegonexus/
│   ├── gui/       ← Dashboard (PySide6)
│   ├── case/      ← إدارة القضايا + Reports + Logs
│   └── core/      ← hashing, entropy, text_hiding, image_stego,
│                    image_steghide, audio_hiding, video_hiding,
│                    pcap_io, network_hiding, malware_lab, forensics
├── tests/         ← test_integration.py + test_requirements.py
├── demo_output/   ← نواتج التجربة (مرفوعة مع المستودع أيضاً)
└── screenshots/   ← لقطات التوثيق
```

---

## 7) ملاحظة أمان أساسية
- كلمات المرور/المفاتيح إلزامية في كل عمليات الإخفاء (لا يوجد "إخفاء بدون مفتاح").
- كل الاختبارات تُجرى على ملفات تجريبية محلية — لا تضع ملفات حساسة في `demo_output/`.
- ألغِ أي توكن GitHub بعد انتهاء الاستخدام.
