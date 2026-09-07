# 📸 لقطات شاشة StegoNexus — التجربة على بيئة كالي

> **البيئة:** Debian 13 (نفس عائلة Kali) مع أدوات Kali الرسمية مثبّتة:
> `file · strings · exiftool · binwalk · steghide · foremost · zsteg`
> **+ ffmpeg/ffprobe** — الأداة ترصدها كلها تلقائياً (7/7).
> كل اللقطات **نتائج حقيقية** (أوامر وأدوات نُفّذت فعلياً، وليست محاكاة).

## 1) ألبوم الواجهة (Dashboard GUI — PySide6)

| اللقطة | الوصف |
|---|---|
| `GUISheet_dashboard.png` | 🖼 ألبوم مجمّع لكل الصفحات العشر |
| `01_dashboard.png` | لوحة التحكم + جدول أدوات كالي (7/7 INSTALLED) |
| `02_forensics_run.png` | ⭐ **Forensics قيد التشغيل**: file/exiftool/binwalk/zsteg/steghide + الإنتروبيا (نتيجة حقيقية على IMG مخفي بـ steghide) |
| `03_hashing.png` | MD5/SHA-1/SHA-256/SHA-512 + مقارنة سلامة |
| `04_text_hiding.png` | Text LSB + Key (تبويبا Hide/Extract) |
| `05_image_hiding.png` | Steghide / CyberHide (تبويبات Hide/Extract/Probe) |
| `06_audio_hiding.png` | LSB · Phase · Spread Spectrum · Metadata + Analyse/Spectrogram |
| `07_video_hiding.png` | VideoHide (ffmpeg/ffprobe) + Container Hiding + Info |
| `08_network_hiding.png` | القنوات الخفية: IP-ID / TCP ISN / Timing (Sender/Receiver/Detection) |
| `09_malware_lab.png` | كشف Evasion (PyInstaller/WinRAR/Sliver/Metasploit) |
| `11_case_management.png` | الحالات + التقارير (MD/JSON/HTML) + سجل التحقيق |

## 2) ألبوم الطرفية (CLI — أوامر حقيقية على Terminal داكن)

| اللقطة | الوصف |
|---|---|
| `CLISheet_terminal.png` | 🖼 ألبوم مجمّع لكل اللقطات الـ11 |
| `cli_01_toolchain.png` | كشف سلسلة أدوات Kali تلقائياً |
| `cli_02_hashing.png` | أوامر hash بأربع خوارزميات |
| `cli_03_text_lsb.png` | hide → reveal لـ Text LSB بالمفتاح |
| `cli_04_image_steghide.png` | ⭐ `image-info --password` + `image-unhide` على صورة steghide حقيقية (Rijndael-128 CBC) |
| `cli_05_audio.png` | 4 طرق صوتية + تحليل |
| `cli_06_video.png` | ffprobe streams + video LSB (ffmpeg حقيقي) |
| `cli_07_network.png` | ⭐ covert stream (832 حزمة) + `COVERT CHANNEL INDICATORS DETECTED` + إعادة تجميع |
| `cli_08_malware.png` | فحص عيّنة: `Loader/C2 artefacts: Metasploit, PyInstaller` |
| `cli_09_forensics.png` | ⭐ تقرير Forensics المجمّع + ملاحظة الإنتروبيا الصادقة |
| `cli_10_case.png` | Case list + export + logs/investigation.log |
| `cli_11_tests.png` | **22/22 اختباراً ناجحاً** |

## 3) ملفات العرض (من `demo.py`)

| الملف | الوصف |
|---|---|
| `cover_art.png` | صورة الغلاف الطبيعية (تُستخدم كغلاف في العرض) |

---

### كيف أُعيد إنتاج اللقطات

```bash
cd StegoNexus
python demo.py                                   # يولّد demo_output/ (كل الأقسام)
python tests/test_integration.py                 # 22/22
QT_QPA_PLATFORM=offscreen python screenshots/capture_gui.py
QT_QPA_PLATFORM=offscreen python screenshots/capture_forensics_run.py
python screenshots/capture_cli.py
python screenshots/make_albums.py
```
