# brdc-downloader

Türkçe konuş. Kullanıcı Türkçe çalışıyor.

NASA CDDIS'ten GPS broadcast ephemeris (BRDC) dosyalarını indiren Windows Tkinter GUI uygulaması.
İsteğe bağlı olarak PortaPack Mayhem için GPS-SIM dosyaları (`.C8` + `.TXT`) üretir.
Depo: `TA3HRJ/brdc-downloader`

## Çalıştırma

```bash
pip install -r requirements.txt    # tek bağımlılık: requests>=2.28
```

Kullanım GUI üzerinden: `BRDC_Downloader.bat` çift tıklanır (konsol penceresi açmaz).
Masaüstü kısayolu için `Create_Desktop_Shortcut.bat` bir kez çalıştırılır.

Gerekenler: Python 3.8+, ücretsiz bir [NASA Earthdata](https://urs.earthdata.nasa.gov/) hesabı,
GPS-SIM özelliği için derlenmiş `gps-sdr-sim` çalıştırılabiliri.

## Yasal uyarı — kaldırma

README'nin en başındaki uyarı kasıtlıdır: simüle GPS sinyali yayınlamak birçok ülkede yasa dışıdır
ve seyrüsefer, havacılık, acil servisleri etkileyebilir. GPS-SIM ile ilgili herhangi bir metni
düzenlerken bu uyarının görünürlüğünü azaltma.

## Notlar

- `BRDC Archive/` indirilen ham veriyi tutar (yüzlerce MB) ve `.gitignore` bu klasörü, ayrıca
  üretilen `.gz`, `.C8`, `.YYn` tiplerini hariç tutar. Bunları commit'e ekleme.
- Tüm uygulama tek dosyada: `brdc_downloader.py` (~29 KB). Earthdata Login kimlik doğrulaması
  `requests` ile yapılır, RINEX 2 ve 3 formatları desteklenir.

## Oturum sonu

Anlamlı bir iş yaptıysan — bir karar verildi, bir şey kırılıp düzeldi, bir varsayım ölçüldü —
bitirmeden önce `docs/HANDOFF.md`'yi güncelle: nerede kalındı, ne açık kaldı, hangi tuzağa
düşüldü ve neden. Dosya yoksa oluştur.

Sohbet geçmişi kalıcı değildir. Repoda yazılı olmayan her şey oturumla birlikte gider.
