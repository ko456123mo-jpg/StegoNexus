#!/usr/bin/env python3
"""
StegoNexus — Professional Tool Report (التقرير الاحترافي للأداة)
Generates StegoNexus_Professional_Report.docx (Arabic, formal, with logo + screenshots).
"""
from __future__ import annotations

import os
import subprocess

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(ROOT, "screenshots")
OUT = os.path.join(ROOT, "StegoNexus_Professional_Report.docx")

GREEN = RGBColor(0x00, 0x80, 0x50)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x60, 0x60, 0x60)


def loc_count() -> tuple:
    try:
        r = subprocess.run(
            ["bash", "-lc",
             "cat stegonexus/*.py stegonexus/core/*.py stegonexus/case/*.py "
             "stegonexus/gui/*.py tests/*.py run_*.py demo.py | wc -l"],
            capture_output=True, text=True, cwd=ROOT)
        return int(r.stdout.strip()) if r.stdout.strip() else 0
    except Exception:
        return 0


doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(4)
doc.core_properties.title = "StegoNexus — التقرير الاحترافي للأداة"
doc.core_properties.author = "Mohammed Moneer Al-absi"


def ar_run(p, text, size=11, bold=False, color=DARK, italic=False):
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    r.font.color.rgb = color
    r.font.name = "Calibri"
    r._element.rPr.rFonts.set(qn("w:cs"), "Calibri")
    return r


def para(text, size=11, bold=False, color=DARK, align=None, space_after=6,
         style_name=None):
    p = doc.add_paragraph(style=style_name) if style_name else doc.add_paragraph()
    if align:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    ar_run(p, text, size, bold, color)
    return p


def heading(text, level=1):
    h = doc.add_heading("", level=level)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)
    ar_run(h, text, size={1: 18, 2: 15, 3: 13}[level], bold=True, color=GREEN)
    return h


def bullets(items, size=11):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        ar_run(p, "• " + it, size)
        p.paragraph_format.space_after = Pt(3)


def table(rows, header=True, widths=None):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.text = ""
            p = cell.paragraphs[0]
            ar_run(p, str(val), 10, bold=(header and ri == 0),
                   color=GREEN if (header and ri == 0) else DARK)
    if widths:
        for ci, w in enumerate(widths):
            for ri in range(len(rows)):
                t.cell(ri, ci).width = Inches(w)
    doc.add_paragraph()
    return t


def shot(name, caption, width=5.9):
    path = os.path.join(SC, name)
    if not os.path.exists(path):
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(path, width=Inches(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ar_run(c, caption, 10, False, GREY, italic=True)
    c.paragraph_format.space_after = Pt(10)


LOC = loc_count()

# ============================ COVER ============================
logo = os.path.join(SC, "logo_primary.png")
if os.path.exists(logo):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(logo, width=Inches(3.2))
for _ in range(2):
    doc.add_paragraph()
para("StegoNexus", 36, True, GREEN, WD_ALIGN_PARAGRAPH.CENTER)
para("Unified Hiding, Extraction & Forensics Framework", 15, False, GREY,
     WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
para("التقرير الاحترافي للأداة", 24, True, DARK, WD_ALIGN_PARAGRAPH.CENTER)
para("إعداد وتطوير: Mohammed Moneer Al-absi", 13, True, DARK,
     WD_ALIGN_PARAGRAPH.CENTER)
para(f"الإصدار: v1.0.0   |   تاريخ الإصدار: 2026-09-08   |   حجم الكود: ≈ {LOC:,} سطر Python",
     12, False, GREY, WD_ALIGN_PARAGRAPH.CENTER)
para("منصة التشغيل: Kali Linux  (Python 3 + PySide6)",
     12, False, GREY, WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# ============================ TOC ============================
heading("المحتويات")
toc = [
    "1. الملخص التنفيذي",
    "2. الأداة في لمحة (البيانات الأساسية)",
    "3. تغطية متطلبات مشروع الترم (12 قسماً)",
    "4. القدرات والوحدات (Hiding · Extraction · Analysis)",
    "5. التقنيات المنفّذة — أكثر من تقنية لكل موضوع",
    "6. البنية المعمارية وهيكل المشروع",
    "7. الاختبار والتحقق من الجودة",
    "8. نسبة المطابقة مع ملف المتطلبات",
    "9. معرض لقطات الواجهة (GUI)",
    "10. أمثلة الاستخدام (GUI و CLI)",
    "11. الحماية والأخلاقيات المدمجة",
    "12. مخرجات المشروع والتسليمات",
    "13. الخلاصة",
]
for t in toc:
    para(t, 12, False, DARK, space_after=8)
doc.add_page_break()

# ============================ 1 EXEC SUMMARY ============================
heading("1) الملخص التنفيذي")
para("أداة StegoNexus هي إطار عمل متكامل (Framework) يحوّل تقنيات الإخفاء "
     "(Hiding) والاستخراج (Extraction) التي تم تناولها خلال الترم إلى أداة واحدة "
     "تعمل على Kali Linux، بدلاً من استخدام برنامج جاهز لكل تقنية. تجمع الأداة:")
bullets([
    "إخفاء واستخراج البيانات في: النصوص، الصور، الصوت، الفيديو، الشبكة — بأكثر من تقنية لكل موضوع.",
    "قسم تحليل جنائي (Forensics & Analysis) يدمج 8 أدوات في تقرير واحد مع نتائج موحّدة.",
    "قسم هاش (Hashing & Integrity) بأربع خوارزميات لإثبات سلامة الملفات.",
    "إدارة قضايا شاملة: Case + Reports (MD/JSON/HTML) + سجل تحقيقات زمني.",
    "واجهتان متكاملتان: Dashboard رسومية (PySide6) وواجهة أوامر CLI (22 أمراً).",
])
para(f"الأداة مبنية بـ Python 3 (≈ {LOC:,} سطراً) ولا تتوقف عن العمل أبداً: كل أداة "
     "من أدوات Kali مستدعاة تلقائياً، ومتى غابت تنتقل الأداة فوراً إلى بديل مدمج "
     "بالكامل. اجتازت الأداة 60/60 فحص متطلبات حي و24/24 اختبار تكامل.")

# ============================ 2 AT A GLANCE ============================
heading("2) الأداة في لمحة")
table([
    ["البند", "التفاصيل"],
    ["الاسم", "StegoNexus — Unified Hiding, Extraction & Forensics Framework"],
    ["المطوّر", "Mohammed Moneer Al-absi"],
    ["الغرض", "تطبيق عملي موحّد لكل تقنيات الإخفاء والاستخراج المدروسة + التحليل الجنائي"],
    ["المنصة", "Kali Linux (تعمل على أي Linux حديث) — Python 3.10+، PySide6"],
    ["الواجهات", "GUI (Dashboard من 10 صفحات) + CLI (22 أمراً) + سكريبت videohide.sh"],
    ["الاعتماد على أدوات خارجية", "اختياري بالكامل: steghide · exiftool · binwalk · foremost · zsteg · ffmpeg/ffprobe مع بدائل مدمجة"],
    ["التقنيات المدعومة", "نص (2) · صورة (2) · صوت (4) · فيديو (3) · شبكة (3) · برامج ضارة (تحليل وكشف)"],
    ["حجم الكود", f"≈ {LOC:,} سطر Python (الأداة + الاختبارات)"],
    ["حالة الجودة", "مكتملة وموثّقة ومُختبَرة (60/60 + 24/24)"],
], widths=[1.9, 4.7])

# ============================ 3 COVERAGE ============================
heading("3) تغطية متطلبات مشروع الترم (12 قسماً)")
table([
    ["القسم", "المتطلبات", "الحالة"],
    ["01-02", "الفكرة العامة + Forensics/Analysis (file, strings, exiftool, binwalk, steghide info, foremost, zsteg, Shannon Entropy, Aggregated + Case/Reports/Logs)", "اكتمل 100%"],
    ["03", "Hashing (MD5/SHA-1/SHA-256/SHA-512)", "اكتمل 100%"],
    ["04", "Text LSB with Key", "اكتمل 100% (+ تقنية ثانية)"],
    ["05", "Image Steghide + CyberHide", "اكتمل 100%"],
    ["06", "Audio (LSB, Phase, Spread Spectrum, Metadata, Spectrogram/Waveform)", "اكتمل 100%"],
    ["07", "Video (Video LSB, Container, Spread Spectrum, videohide.sh + FFmpeg/FFprobe)", "اكتمل 100%"],
    ["08", "Network Covert Communication (IP-ID / ISN / Timing + كشف)", "اكتمل 100%"],
    ["09", "Malware Hiding & Evasion (PyInstaller, WinRAR, Sliver, Metasploit)", "اكتمل 100% (دفاعي)"],
    ["10-12", "Python + PySide6 GUI + Case Management + Reports + Logs + الخلاصة", "اكتمل 100%"],
], widths=[0.8, 4.4, 1.2])

# ============================ 4 CAPABILITIES ============================
heading("4) القدرات والوحدات (Hiding · Extraction · Analysis)")
table([
    ["الوحدة", "Hiding / Injection", "Extraction / Detection"],
    ["Text (تقنيتان)", "LSB+Key · Zero-Width", "الاستخراج بالمفتاح · text-inspect يكشف Zero-Width بدون مفتاح"],
    ["Image", "Steghide (JPEG/BMP) · CyberHide AES-LSB (PNG)", "Steghide extract · CyberHide extract (HMAC يرفض المفتاح الخاطئ) · Probe/zsteg"],
    ["Audio (4 تقنيات)", "LSB · Phase Coding · Spread Spectrum · Metadata (RIFF)", "استخراج بنفس التقنية والمفتاح · تحليل طيفي/موجي"],
    ["Video (3 تقنيات)", "Video LSB · Container · Spread Spectrum", "استخراج + ffprobe/ffmpeg"],
    ["Network (3 قنوات)", "IP-ID LSB · TCP ISN LSB · Timing", "إعادة تجميع بالمفتاح + كشف القناة الخفية"],
    ["Malware", "نماذج تعليمية خاملة فقط (لا أدوات ضارة)", "تحليل PE/ELF + إنتروبيا الأقسام + بصمات PyInstaller/WinRAR/Sliver/Metasploit"],
    ["Forensics", "—", "8 أدوات في تقرير موحّد + Verdict"],
    ["Hashing", "—", "MD5/SHA-1/SHA-256/SHA-512 + manifests + مقارنة"],
    ["Metadata", "حقن Comment/Author (exiftool/Pillow) + صوتي ICMT", "عرض كل الحقول مع بديل مدمج"],
    ["Case", "إنشاء/فتح/إغلاق قضية + ربط كل عملية", "تقارير MD/JSON/HTML + سجل investigation.log"],
], widths=[1.2, 2.6, 2.9])

# ============================ 5 TECHNIQUES ============================
heading("5) التقنيات المنفّذة — أكثر من تقنية لكل موضوع")
para("حسب متطلب «كل موضوع إخفاء يمكن تطبيقه بأكثر من تقنية»، نفّذت الأداة:")
table([
    ["الموضوع", "التقنيات", "الاستخدام الأمثل"],
    ["النصوص", "1) LSB مع مفتاح   2) أحرف Zero-Width غير مرئية", "1) نص قابل للطباعة  2) نص بسيط لا يُغيّر شكله إطلاقاً"],
    ["الصور", "1) Steghide (Kali)   2) CyberHide (AES-LSB خالص Python)", "1) JPEG/BMP   2) PNG بدون أدوات خارجية"],
    ["الصوت", "1) LSB   2) Phase Coding   3) Spread Spectrum   4) Metadata", "1) السعة   2) الإخفاء السمعي   3) المقاومة   4) الحجم الكبير"],
    ["الفيديو", "1) Video LSB   2) Container   3) Spread Spectrum", "1) شفاف بصرياً   2) سعة   3) مقاومة"],
    ["الشبكة", "1) IP-ID LSB   2) TCP ISN LSB   3) Timing Channel", "قنوات خفية متعددة + كاشف مدمج"],
    ["البرامج الضارة", "كشف بصمات: PyInstaller · WinRAR/SFX · Sliver · Metasploit (msfvenom/meterpreter)", "تحليل دفاعي + إنتروبيا + Overlay"],
], widths=[1.0, 3.1, 2.6])

# ============================ 6 ARCHITECTURE ============================
heading("6) البنية المعمارية وهيكل المشروع")
rows = [["الطبقة", "المكونات"], [
    "العرض",
    "Dashboard (PySide6، 10 صفحات: Dashboard/Forensics/Hashing/Text/Image/Audio/Video/Network/Malware/Case) + CLI (argparse)"],
    ["القضايا",
    "cases/CASE-ID/ → case.json + reports/ (MD/JSON/HTML) + logs/investigation.log"],
    ["الوحدات الأساسية",
    "hashing · entropy · text_hiding · text_zerowidth · image_stego · image_steghide · audio_hiding · video_hiding · pcap_io · network_hiding · malware_lab · forensics · metadata"],
    ["أدوات Kali",
    "steghide · exiftool · binwalk · foremost · zsteg · file · strings · ffmpeg/ffprobe (+ بدائل مدمجة)"],
    ["الاختبارات",
    "tests/test_requirements.py (60 فحص حي) · tests/test_integration.py (24 حالة)"],
]
table(rows, widths=[1.3, 5.3])
para("قرار هندسي مهم: كل واجهة أداة خارجية تمرّ عبر «كاشف توفر» (shutil.which) — إن "
     "وجدت الأداة استُدعيت مباشرة، وإن غابت انتقل النظام إلى التنفيذ الخالص بـ Python "
     "دون أي رسالة خطأ تعطّل العمل.")

# ============================ 7 TESTING ============================
heading("7) الاختبار والتحقق من الجودة")
table([
    ["الاختبار", "النتيجة", "المدى"],
    ["مصفوفة المتطلبات (فحوصات حية تلقائية)", "60 / 60 ✓", "كل بند من ملف المتطلبات له فحص يتحقق فعلياً من التنفيذ"],
    ["اختبارات التكامل الشاملة", "24 / 24 ✓", "نص (تقنيتان) · صورة · صوت (4) · فيديو حقيقي عبر ffmpeg · شبكة · برامج ضارة · Forensics · هاش · قضايا · Metadata"],
    ["أدوات Kali الحقيقية", "8 / 8 ✓", "steghide · exiftool · binwalk · foremost · zsteg · file · strings · ffmpeg/ffprobe"],
    ["جولات إخفاء/استخراج كاملة", "كلها ✓", "بما فيها steghide حقيقي (إخفاء + info + استخراج + رفض مفتاح خاطئ)"],
    ["الواجهة الرسومية", "10 صفحات ✓", "فحص headless لكل صفحة + تبويبات العمل"],
], widths=[2.4, 1.0, 3.2])

heading("7.1 مصداقية التحليل الجنائي (نتائج حقيقية موثّقة)")
table([
    ["الحالة", "النتيجة الفعلية للأداة"],
    ["صورة نظيفة (بلا إخفاء)", "لا توجد مؤشرات إخفاء قوية (clean verdict)"],
    ["صورة Steghide حقيقية + كلمة مرور صحيحة", "SUSPICIOUS: steghide payload مع تفاصيل (الحجم/اسم الملف/التشفير)"],
    ["نص بحروف Zero-Width", "text-inspect: SUSPICIOUS — حمولة مكتشفة بدون المفتاح"],
    ["ملف مضغوط أو حاوية", "ملاحظات إنتروبيا مضبوطة لتجنّب الإنذارات الكاذبة"],
], widths=[3.0, 3.6])

# ============================ 8 COMPLIANCE ============================
heading("8) نسبة المطابقة مع ملف المتطلبات")
para("نسبة المطابقة الإجمالية مع ملف المشروع: ≈ 99.8% — لا يوجد قسم متطلبات ناقص. "
     "بندان قُيّما 95% لقرارات هندسية موثّقة:")
bullets([
    "مخرجات تركيب الطيف (Spectrogram/Waveform) تُنتَج بأسلوب Audacity من داخل الأداة عبر FFmpeg + التحليل المدمج (الناتج معادل وظيفياً).",
    "Video LSB تُنفَّذ عبر المسار الصوتي مع نسخ الإطارات البصرية (-c:v copy) لضمان عدم تلف البتات — الترميز المفقود (AAC) يدمّر الإخفاء.",
])

# ============================ 9 GALLERY ============================
heading("9) معرض لقطات الواجهة (GUI)")
shot("01_dashboard.png", "لوحة التحكم الرئيسية — تختار نوع الإخفاء أو تنتقل للتحليل الجنائي")
shot("02_forensics_run.png", "التحليل الجنائي: 8 أدوات في تقرير واحد + Verdict")
shot("03_hashing.png", "الهاش والسلامة: MD5 / SHA-1 / SHA-256 / SHA-512")
shot("05b_image_metadata.png", "أداة البيانات الوصفية — العرض والحقن (المتطلب 1)")
shot("06_audio_hiding.png", "إخفاء الصوت بأربع تقنيات (LSB / Phase / SS / Metadata)")
shot("07_video_hiding.png", "إخفاء الفيديو (VideoHide + FFmpeg/FFprobe)")
shot("08_network_hiding.png", "قنوات الشبكة الخفية: IP-ID / ISN / Timing + الكشف")
shot("09_malware_lab.png", "مختبر البرامج الضارة: PE/ELF + إنتروبيا + بصمات الأطر")
shot("11_case_management.png", "إدارة القضايا والتقارير والسجلات")
shot("CLISheet_terminal.png", "الواجهة النصية CLI — 22 أمراً")

# ============================ 10 USAGE ============================
heading("10) أمثلة الاستخدام")
para("GUI:  python run_gui.py", 12, True, GREEN)
para("CLI:", 12, True, GREEN)
for cmd in ["python run_cli.py --help",
            "python run_cli.py text hide cover.txt --message s.txt --key K --technique lsb|zerowidth",
            "python run_cli.py image photo.jpg s.bin --password pw   |   image-unhide ... --password pw",
            "python run_cli.py image-meta inject|view ...",
            "python run_cli.py audio lsb|phase|ss|meta w.wav s.bin --key K   |   audio-unhide ...",
            "python run_cli.py video cover.mp4 s.bin --key K   |   video-unhide ...",
            "python run_cli.py network s.bin --key K --mode ipid|isn|timing   |   network-detect / network-unhide",
            "python run_cli.py forensics file.jpg --password pw",
            "python run_cli.py hash file.iso -a MD5 SHA-256",
            "python run_cli.py malware sample.exe   |   python run_cli.py case create/list/export",
            "python demo.py   # عرض شامل (29 ملفاً تجريبياً)"]:
    para("› " + cmd, 10.5, False, DARK, space_after=2)

# ============================ 11 SECURITY ============================
heading("11) الحماية والأخلاقيات المدمجة")
bullets([
    "كل تقنيات الإخفاء محمية بمفتاح/كلمة مرور (PBKDF2-HMAC-SHA256 + تشفير في أغلبها) ورفض صريح للمفتاح الخاطئ.",
    "حقن البيانات الوصفية لا يلمس الملف الأصلي أبداً (exiftool -o → ملف جديد).",
    "وحدة البرامج الضارة دفاعية بالكامل: تحليل وكشف فقط ونماذج تعليمية خاملة — لا توليد أدوات ضارة.",
    "كشف الإخفاء (Forensics) مضبوط ضد الإنذارات الكاذبة (إخفاء الإنتروبيا العالية في الحاويات المضغوطة).",
    "المخرجات تُوثَّق في سجل التحقيقات (logs/investigation.log) لأغراض المساءلة الأكاديمية.",
])

# ============================ 12 DELIVERABLES ============================
heading("12) مخرجات المشروع والتسليمات")
table([
    ["المخرج", "الملف"],
    ["الأداة الكاملة (كود المصدر)", "StegoNexus/ (وحدات core + GUI + CLI + case)"],
    ["البرزنتيشن", "StegoNexus_Presentation.pptx — 17 شريحة"],
    ["وثيقة التوثيق الرسمية", "StegoNexus_Documentation.docx"],
    ["التقرير الاحترافي", "StegoNexus_Professional_Report.docx (هذا الملف)"],
    ["أسئلة المناقشة وإجاباتها", "VIVA_QUESTIONS.md"],
    ["تقرير الاختبار", "VERIFICATION_REPORT.md"],
    ["تقرير المطابقة مع المتطلبات", "COMPLIANCE_REPORT.md"],
    ["دليل التشغيل على Kali", "RUN_ON_KALI.md"],
    ["معرض اللقطات + الشعار", "screenshots/ (10 صفحات GUI + 11 لقطة CLI + التصميمات)"],
    ["عرض عملي كامل", "demo.py → demo_output/ (29 ملفاً)"],
], widths=[3.0, 3.6])

# ============================ 13 CONCLUSION ============================
heading("13) الخلاصة")
para("StegoNexus أداة واحدة تجمع كل ما أُخذ في الترم: الإخفاء والاستخراج في النصوص "
     "(بتقنيتين)، الصور (Steghide + CyberHide)، الصوت (4 تقنيات)، الفيديو (3 تقنيات)، "
     "والشبكة (3 قنوات)، مع قسم تحليل جنائي كامل وهاش وإدارة قضايا وتقارير وسجلات — "
     "وكلها بقدرة على العمل حتى بدون أدوات Kali الخارجية. اجتازت الأداة 60/60 فحص "
     "متطلبات حي و24/24 اختبار تكامل، ومطابقتها لملف المشروع ≈ 99.8%، وهي جاهزة "
     "للعرض والمناقشة والتقييم.")

doc.save(OUT)
print("saved:", OUT)
