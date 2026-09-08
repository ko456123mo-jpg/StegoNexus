#!/usr/bin/env python3
"""
StegoNexus — Project Presentation (برزنتيشن المشروع)
Generates StegoNexus_Presentation.pptx (16:9, bilingual AR/EN, 17 slides)
with real screenshots embedded.
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(ROOT, "screenshots")
OUT = os.path.join(ROOT, "StegoNexus_Presentation.pptx")

DARK = RGBColor(0x0F, 0x11, 0x17)
PANEL = RGBColor(0x16, 0x1B, 0x22)
GREEN = RGBColor(0x00, 0xD9, 0x8B)
WHITE = RGBColor(0xE6, 0xE6, 0xE6)
GREY = RGBColor(0x9A, 0xA4, 0xB5)
YELLOW = RGBColor(0xFF, 0xD1, 0x66)

W, H = Inches(13.333), Inches(7.5)


def set_rtl(par):
    """Mark a paragraph as RTL (right-to-left, for Arabic)."""
    pPr = par._p.get_or_add_pPr()
    pPr.set("rtl", "1")
    pPr.set("algn", "r")


def add_text(slide, x, y, w, h, runs, align=PP_ALIGN.LEFT, rtl=False,
             anchor=MSO_ANCHOR.TOP, space_after=6):
    """runs = [(text, size, bold, color), ...] one per line."""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, (text, size, bold, color) in enumerate(runs):
        par = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        par.alignment = align
        par.space_after = Pt(space_after)
        run = par.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = "Segoe UI"
        if rtl:
            set_rtl(par)
    return box


def slide_blank(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid(); bg.fill.fore_color.rgb = DARK
    bg.line.fill.background()
    bg.shadow.inherit = False
    return s


def title_bar(slide, num, ar_title, en_title):
    add_text(slide, Inches(0.6), Inches(0.32), Inches(12.1), Inches(0.9),
             [(ar_title, 26, True, GREEN), (en_title, 13, False, GREY)])
    tag = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(11.9),
                                 Inches(0.35), Inches(0.85), Inches(0.45))
    tag.fill.solid(); tag.fill.fore_color.rgb = GREEN
    tag.line.fill.background(); tag.shadow.inherit = False
    tf = tag.text_frame
    tf.text = str(num)
    tf.paragraphs[0].alignment = PP_ALIGN.CENTER
    tf.paragraphs[0].runs[0].font.size = Pt(16)
    tf.paragraphs[0].runs[0].font.bold = True
    tf.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x08, 0x13, 0x0D)
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.18),
                                  Inches(12.1), Pt(2.2))
    line.fill.solid(); line.fill.fore_color.rgb = GREEN
    line.line.fill.background(); line.shadow.inherit = False


def bullets(slide, items, x=Inches(0.8), y=Inches(1.55), w=Inches(11.7),
            size=15, gap=8, color=WHITE, rtl=False):
    runs = []
    for it in items:
        dot = "• " if not rtl else "• "
        runs.append((dot + it, size, False, color))
    add_text(slide, x, y, w, Inches(len(items) * 0.42), runs, rtl=rtl,
             space_after=gap)


def pic(slide, path, x, y, w):
    try:
        slide.shapes.add_picture(path, x, y, width=w)
    except Exception:
        pass


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # ---------------- 1 TITLE ----------------
    s = slide_blank(prs)
    hero = os.path.join(SC, "hero_banner.png")
    if os.path.exists(hero):
        shop = s.shapes.add_picture(hero, Inches(0), Inches(0), width=W)
        shop.crop_top = 0.0
    add_text(s, Inches(0.8), Inches(2.2), Inches(11.7), Inches(3.4), [
        ("StegoNexus", 60, True, GREEN),
        ("Unified Hiding, Extraction & Forensics Framework", 22, False, WHITE),
        ("إطار موحّد للإخفاء والاستخراج والتحليل الجنائي الرقمي", 18, False, GREY),
        ("", 8, False, GREY),
        ("Prepared & Developed by:  Mohammed Moneer Al-absi", 16, True, YELLOW),
    ], align=PP_ALIGN.CENTER)

    # ---------------- 2 AGENDA ----------------
    s = slide_blank(prs)
    title_bar(s, "0", "محتويات العرض", "Agenda")
    bullets(s, [
        "الفكرة العامة والبنية المعمارية — General Overview & Architecture",
        "التحليل الجنائي (Forensics & Analysis) والهاش (Hashing & Integrity)",
        "إخفاء النصوص (Text LSB + Key) والصور (Steghide / CyberHide)",
        "إخفاء الصوت (LSB · Phase · Spread Spectrum · Metadata) والفيديو (VideoHide)",
        "إخفاء الشبكة (Covert Channels) والبرامج الضارة (Evasion Lab)",
        "إدارة القضايا والتقارير — Case Management & Reports",
        "نتائج الاختبار والعرض الحي — Live Demo & Verification",
    ], size=17, gap=10)

    # ---------------- 3 OVERVIEW ----------------
    s = slide_blank(prs)
    title_bar(s, "01", "الفكرة العامة", "General Overview")
    bullets(s, [
        "تحويل تقنيات الإخفاء والاستخراج التي أُخذت خلال الترم إلى أداة واحدة متكاملة تعمل على Kali Linux.",
        "Dashboard موحّدة تسمح باختيار نوع الإخفاء أو الانتقال إلى قسم Forensics لفحص الملفات.",
        "دمج أدوات Kali الجاهزة + السكريبتات والتقنيات المطوّرة، بدل الاعتماد على أداة واحدة.",
        "كل النتائج تُربط بملف Case وتُحفظ ضمن Reports و Logs.",
    ], size=16, gap=12)

    # ---------------- 4 ARCHITECTURE ----------------
    s = slide_blank(prs)
    title_bar(s, "01", "البنية المعمارية", "Architecture")
    layers = [
        ("Presentation Layer", "GUI (PySide6 Dashboard)  |  CLI (argparse)"),
        ("Case Layer", "cases/CASE-ID/ → case.json + reports (MD/JSON/HTML) + logs/investigation.log"),
        ("Core Modules", "hashing · entropy · text_hiding · image_stego · image_steghide · audio_hiding · video_hiding · pcap_io · network_hiding · malware_lab · forensics · metadata"),
        ("External Tools (auto-detect)", "steghide · exiftool · binwalk · foremost · zsteg · file · strings · ffmpeg/ffprobe   + built-in fallbacks"),
    ]
    y = 1.6
    for name, desc in layers:
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8),
                                 Inches(y), Inches(11.7), Inches(1.15))
        box.fill.solid(); box.fill.fore_color.rgb = PANEL
        box.line.color.rgb = GREEN; box.line.width = Pt(1)
        box.shadow.inherit = False
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run(); r.text = name
        r.font.size = Pt(15); r.font.bold = True; r.font.color.rgb = GREEN
        p2 = tf.add_paragraph()
        r2 = p2.add_run(); r2.text = desc
        r2.font.size = Pt(12); r2.font.color.rgb = WHITE
        y += 1.32

    # ---------------- 5 FOREnsics ----------------
    s = slide_blank(prs)
    title_bar(s, "02", "التحليل الجنائي والاستعلام", "Forensics & Analysis")
    bullets(s, [
        "file → معرفة النوع الحقيقي للملف من الترويسات (مع بديل Magic مدمج)",
        "strings → استخراج النصوص القابلة للقراءة + تصنيف كلمات مفتاحية",
        "exiftool → عرض البيانات الوصفية Metadata (مع بديل Pillow)",
        "binwalk → البحث عن الملفات والتوقيعات المدمجة في الملف",
        "steghide info → التحقق من وجود بيانات مخفية (يتطلب كلمة المرور للتنفيذ)",
        "foremost → استخراج الملفات من الملفات (File Carving)",
        "zsteg → تحليل طبقات LSB في الصور (مع بديل مدمج)",
        "Shannon Entropy → قياس العشوائية لكشف المناطق/الملفات المخفية",
    ], size=14, gap=7)
    pic(s, os.path.join(SC, "02_forensics_run.png"), Inches(0.8), Inches(4.6),
        Inches(5.6))
    add_text(s, Inches(6.8), Inches(4.7), Inches(5.9), Inches(2.4), [
        ("النتيجة المتوقعة:", 14, True, YELLOW),
        ("تجميع نتائج الأدوات في واجهة واحدة وربطها بملف Case وإمكانية حفظها ضمن Reports و Logs", 13, False, WHITE),
        ("", 6, False, WHITE),
        ("Verdict التجربة الحية:", 14, True, GREEN),
        ("SUSPICIOUS: steghide payload", 13, False, GREEN),
    ])

    # ---------------- 6 HASHING ----------------
    s = slide_blank(prs)
    title_bar(s, "03", "الهاش والسلامة", "Hashing & Integrity")
    bullets(s, [
        "MD5 · SHA-1 · SHA-256 · SHA-512 — بث على ملفات كبيرة (1MiB) لتوفير الذاكرة",
        "جزء مستقل للتحقق من سلامة الملفات قبل وبعد عمليات الإخفاء والاستخراج",
        "تسجيل قيم الـ Hash ضمن ملف القضية Case والمطابقة في التقارير لتوثيق الملفات وتتبع التغييرات",
        "مقارنة ملفين (compare) + إنشاء/التحقق من manifests",
    ], size=16, gap=12)
    add_text(s, Inches(0.8), Inches(4.9), Inches(11.7), Inches(1.6), [
        ("مثال حي:", 14, True, YELLOW),
        ("python run_cli.py hash server.iso -a MD5 SHA-256", 15, False, GREEN),
        ("SHA-256  b8bbbe60...44f3   stegonexus/__init__.py", 13, False, WHITE),
    ])

    # ---------------- 7 TEXT ----------------
    s = slide_blank(prs)
    title_bar(s, "04", "إخفاء النصوص — تقنيتان", "Text Hiding — LSB with Key + Zero-Width")
    add_text(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(1.0), [
        ("Python implementation داخل الأداة (بدل برنامج جاهز) — تقنيتان لكل موضوع", 15, True, WHITE),
    ])
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8),
                             Inches(2.1), Inches(11.7), Inches(1.9))
    box.fill.solid(); box.fill.fore_color.rgb = PANEL
    box.line.color.rgb = GREEN; box.shadow.inherit = False
    tf = box.text_frame; tf.word_wrap = True
    for i, line in enumerate([
        "Hiding / Encoding     :  Cover Text + Secret Message + Key  →  LSB Encoding  →  Stego Text",
        "Extraction / Decoding :  Stego Text + Key  →  LSB Decoding  →  Original Secret Message"]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = line
        r.font.size = Pt(14); r.font.color.rgb = WHITE
    bullets(s, [
        "السر يُشفَّر بتيار مفتاح مشتق من المفتاح (PBKDF2-HMAC-SHA256) ثم يُخفى في LSB لرموز النص",
        "تبديل مواضع الحاملات مبني على المفتاح → بدون المفتاح لا يمكن إعادة التجميع (رفض المفتاح الخاطئ)",
    ], y=3.7, size=14, gap=6)
    bullets(s, [
        "التقنية الثانية (Zero-Width): أزواج البتات تُرمَّز بأحرف غير مرئية (U+200B/U+200C/U+200D/U+FEFF) موزعة داخل النص بتباعد مفتاحي — النص يبدو عادياً تماماً",
        "الكشف: text-inspect يقرأ الأحرف غير المرئية ويكتشف الحمولة **بدون المفتاح**",
    ], y=4.9, size=13, gap=6)

    # ---------------- 8 IMAGE ----------------
    s = slide_blank(prs)
    title_bar(s, "05", "إخفاء الصور — Steghide و CyberHide", "Image Hiding")
    bullets(s, [
        "Hiding     :  Image + Secret File + Password → Steghide → Stego Image",
        "Extraction :  Stego Image + Password → Steghide → Original Secret File",
        "Steghide (Kali): JPEG/BMP, تشفير Rijndael-128 CBC وضغط — جُرّب فعلياً في بيئة كالي",
        "CyberHide مدمج (بديل خالص بـ Python): AES-256-CBC + HMAC-SHA256 + تبديل قنوات بالمفتاح",
        "الكشف: kلمة المرور الصحيحة تُظهر التفاصيل (اسم الملف، الحجم، التشفير) والمفتاح الخاطئ يُرفض",
    ], size=15, gap=10)
    pic(s, os.path.join(SC, "05_image_hiding.png"), Inches(0.8), Inches(4.6),
        Inches(5.9))

    # ---------------- 8b METADATA (view + inject) ----------------
    s = slide_blank(prs)
    title_bar(s, "05+", "أداة البيانات الوصفية — عرض وحقن", "Metadata View & Inject (requirement item 1)")
    pic(s, os.path.join(SC, "05b_image_metadata.png"), Inches(0.55), Inches(1.45),
        Inches(7.0))
    add_text(s, Inches(7.9), Inches(1.6), Inches(4.9), Inches(5.4), [
        ("المتطلب:", 15, True, YELLOW),
        ("أداة تعرض البيانات الوصفية وأيضاً أداة تحقنها", 14, False, WHITE),
        ("", 8, False, WHITE),
        ("View:", 15, True, GREEN),
        ("exiftool (Kali) لعرض كل حقول الملف مع بديل Pillow كامل", 13, False, WHITE),
        ("", 8, False, WHITE),
        ("Inject:", 15, True, GREEN),
        ("exiftool -Comment/-Artist مع -o (لا يُلمس الأصل أبداً) / PNG tEXt / JPEG COM", 13, False, WHITE),
        ("", 8, False, WHITE),
        ("امتداد الصوت:", 15, True, GREEN),
        ("حقن RIFF LIST-INFO (ICMT) عبر وحدة الصوت", 13, False, WHITE),
        ("", 8, False, WHITE),
        ("تحقق فوري:", 15, True, GREEN),
        ("إعادة قراءة البيانات بعد الحقن والتحقق من وجودها (verified)", 13, False, WHITE),
        ("", 8, False, WHITE),
        ("CLI:", 15, True, YELLOW),
        ("image-meta view|inject", 14, False, GREEN),
    ], rtl=False)

    # ---------------- 9 AUDIO ----------------
    s = slide_blank(prs)
    title_bar(s, "06", "إخفاء الصوت", "Audio Hiding")
    add_text(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.8), [
        ("أربع تقنيات رئيسية (أكثر من تقنية في نفس الموضوع — حسب المتطلبات):", 15, True, WHITE)])
    bullets(s, [
        "LSB  — إخفاء البيانات داخل Least Significant Bits لعينات الصوت (تبديل مواضع بالمفتاح)",
        "Phase Coding  — تعديل معلومات الـ Phase (فرق ±π/2 بين إطارات FFT متتالية)",
        "Spread Spectrum  — نشر البيانات على نطاق ترددات بدل موضع واحد (DSSS-BPSK)",
        "Metadata  — إخفاء البيانات داخل الملف الصوتي دون تعديل العينات (RIFF LIST-INFO / ICMT)",
        "التحليل: Steghide (للحالات التي يدعمها) + Spectrogram Frequency Analysis و Waveform (مخرجات Audacity)",
    ], y=2.35, size=14, gap=8)
    pic(s, os.path.join(SC, "06_audio_hiding.png"), Inches(0.8), Inches(5.15),
        Inches(5.7))

    # ---------------- 10 VIDEO ----------------
    s = slide_blank(prs)
    title_bar(s, "07", "إخفاء الفيديو — VideoHide", "Video Hiding")
    bullets(s, [
        "لا يعتمد على برنامج جاهز واحد: VideoHide module + سكريبت videohide.sh + FFmpeg + FFprobe",
        "Video LSB  — تعديل LSB في المسار الصوتي للفيديو مع نسخ الإطارات البصرية كما هي (-c:v copy) → صفر تغيير بصري",
        "Container / File Hiding  — استغلال ملف الفيديو لإخفاء بيانات إضافية (حمولة مشفّرة + تذييل موقّع)",
        "Spread Spectrum  — نشر البيانات داخل معلومات الفيديو (DSSS على المسار الصوتي)",
        "التحليل: ffprobe يعرض الـ Streams (codec / bitrate / duration), FFmpeg يستخرج ويعيد ترميز الصوت",
    ], size=15, gap=10)
    pic(s, os.path.join(SC, "07_video_hiding.png"), Inches(0.8), Inches(4.7),
        Inches(5.8))

    # ---------------- 11 NETWORK ----------------
    s = slide_blank(prs)
    title_bar(s, "08", "إخفاء الشبكة — اتصال خفي", "Network Hiding — Covert Communication")
    add_text(s, Inches(0.8), Inches(1.5), Inches(11.7), Inches(0.9), [
        ("Sender  :  Secret Data → Hide/Encode into Network Traffic → Transmit", 14, True, WHITE),
        ("Receiver:  Receive Traffic → Read/Detect Hidden Data → Extract/Reassemble Original Data", 14, True, WHITE)])
    bullets(s, [
        "IPv4 Identification (IP ID) LSB — بت في حقل معرف الحزمة",
        "TCP Initial Sequence Number (ISN) LSB — بت في الرقم التسلسلي الأول",
        "Covert Timing Channel — بت في التأخير بين الحزم",
        "بناء حزم Ethernet/IPv4/TCP يدوياً بـ Python (مكتبة pcap خاصة) + إمكانية البث الحي (scapy)",
        "كشف تلقائي للقناة الخفية: نمط LSB متوازن غير متناوب / تأخيرات ثنائية النمط",
    ], y=2.8, size=14, gap=8)

    # ---------------- 12 MALWARE ----------------
    s = slide_blank(prs)
    title_bar(s, "09", "البرامج الضارة والإخفاء والتهرب", "Malware Hiding & Evasion")
    bullets(s, [
        "دراسة تقنيات Malware Hiding وتحليل العينات واكتشاف مؤشرات Evasion",
        "فحص Payloads / Executables (PE + ELF) وربط النتائج بـ Forensics",
        "الكشف عن مؤشرات الأدوات: PyInstaller (MEI/٬PYZ) · WinRAR (Rar!/SFX) · Sliver · Metasploit (meterpreter/msfvenom)",
        "إنتروبيا الأقسام > 7.0 → احتمال ترميز/تغليف، والـ Overlay → بيانات ملحقة",
        "التركيز على التحليل والكشف والفهم الأكاديمي للتقنيات (نماذج خاملة فقط — لا تُنتج أدوات ضارة)",
    ], size=15, gap=12)

    # ---------------- 13 CASE ----------------
    s = slide_blank(prs)
    title_bar(s, "10-11", "إدارة القضايا والتقارير", "Case Management & Reports")
    bullets(s, [
        "Cases Management  — إنشاء/فتح/إغلاق القضايا + الأدلة والنتائج المرتبطة بها",
        "Reports Generation  — تصدير التقارير بصيغ Markdown / JSON / HTML",
        "Investigation Logs  — سجل تحقيقات زمني (logs/investigation.log) يسجّل كل عملية تلقائياً",
        "كل عملية إخفاء/استخراج/فحص في الواجهة تُسجَّل في القضية النشطة تلقائياً",
    ], size=16, gap=12)
    pic(s, os.path.join(SC, "11_case_management.png"), Inches(0.8), Inches(4.5),
        Inches(5.7))

    # ---------------- 14 DEMO ----------------
    s = slide_blank(prs)
    title_bar(s, "DEMO", "عرض النتائج الحية", "Live Results & Screenshots")
    pic(s, os.path.join(SC, "GUISheet_dashboard.png"), Inches(0.55), Inches(1.45),
        Inches(6.0))
    pic(s, os.path.join(SC, "CLISheet_terminal.png"), Inches(6.75), Inches(1.45),
        Inches(6.0))
    add_text(s, Inches(0.55), Inches(6.7), Inches(12.2), Inches(0.6), [
        ("GUI: 10 صفحات ·  CLI: 22 أمراً ·  أدوات كالي 8/8 مُرصودة تلقائياً", 14, True, GREEN)],
        align=PP_ALIGN.CENTER)

    # ---------------- 15 TESTING ----------------
    s = slide_blank(prs)
    title_bar(s, "TEST", "نتائج التحقق", "Verification Results")
    rows = [
        ("اختبارات التكامل (كل وحدة دالة)", "24 / 24  ✓", GREEN),
        ("مصفوفة المتطلبات (كل بند بفحص حي)", "60 / 60  ✓", GREEN),
        ("أدوات Kali الحقيقية المثبتة (steghide, exiftool, binwalk, foremost, zsteg, ffmpeg…) ", "8 / 8  ✓", GREEN),
        ("جولات إخفاء/استخراج كاملة (نص·صورة·صوت×4·فيديو×3·شبكة×3)", "كلها ✓", GREEN),
        ("مطابقة ملف المتطلبات PDF (12 قسماً)", "≈ 99.8 %", YELLOW),
    ]
    y = 1.8
    for name, val, col in rows:
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9),
                                 Inches(y), Inches(11.5), Inches(0.75))
        box.fill.solid(); box.fill.fore_color.rgb = PANEL
        box.line.color.rgb = col; box.shadow.inherit = False
        tf = box.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]
        r = p.add_run(); r.text = name
        r.font.size = Pt(15); r.font.color.rgb = WHITE
        p2 = tf.add_paragraph(); p2.alignment = PP_ALIGN.RIGHT
        r2 = p2.add_run(); r2.text = val
        r2.font.size = Pt(15); r2.font.bold = True; r2.font.color.rgb = col
        y += 0.92

    # ---------------- 16 CONCLUSION ----------------
    s = slide_blank(prs)
    title_bar(s, "12", "الخلاصة", "Conclusion")
    bullets(s, [
        "StegoNexus هو Framework موحّد يجمع تقنيات الإخفاء لـ (Text + Image + Audio + Video + Network)",
        "مع دعم عمليات الإخفاء والاسترجاع للتقنيات المذكورة + قسم مستقل لـ Malware",
        "وفوق ذلك: Forensics / Analysis و Hashing و Reports و Logs",
        "جوهر المشروع: دمج أدوات Kali الجاهزة مع السكريبتات والتقنيات المطوّرة، وتقديمها كلها عبر Dashboard واحدة منظمة بدل استخدام كل أداة على حدة",
    ], size=16, gap=12)
    add_text(s, Inches(0.8), Inches(5.6), Inches(11.7), Inches(1.2), [
        ("شكراً لحسن استماعكم — أسئلة؟", 22, True, GREEN),
        ("Thanks for listening — Questions?  |  Mohammed Moneer Al-absi", 14, False, GREY)],
        align=PP_ALIGN.CENTER)

    prs.save(OUT)
    print("saved:", OUT, "| slides:", len(prs.slides._sldIdLst))


if __name__ == "__main__":
    main()
