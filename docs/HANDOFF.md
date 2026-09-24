# HANDOFF

## Son durum (2026-09-25)

- 2026-09-06 oturumunda çıkan öneri listesindeki işlerin hepsi kapandı (aşağıda).
  Bilinen açık kod işi yok.
- Hiçbir değişiklik gerçek bir CDDIS indirmesi ya da gerçek `gps-sdr-sim` ile denenmedi.
  Doğrulama, ağı ve alt süreci taklit eden arayüzsüz testlerle yapıldı (aşağıda). İlk gerçek
  kullanımda bakılacaklar: Cancel `gps-sdr-sim`'i gerçekten durduruyor mu, boyut tahmini
  gerçek `.C8` boyutuyla tutuyor mu.

## Bu makinenin durumu (repo dışı)

- `requests` 2026-09-24'te kuruldu (requests 2.34.2, Python 3.13.15). `BRDC_Downloader.bat`
  ile uygulama açıldı, pencere geldi, `brdc_error.log` oluşmadı.
- **PATH tuzağı:** `WindowsApps\python3` (Microsoft Store yönlendiricisi) PATH'te Python313'ten
  önce geliyor. Git Bash'te `python` "Python was not found" diyor; tam yol kullan:
  `C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe`.
  `BRDC_Downloader.bat` `pythonw` çağırıyor; o Python313'ten geliyor ve çalışıyor.
- **`gps-sdr-sim.exe` yok.** Uygulama önce `C:\Claude Projects\gps-sdr-sim\gps-sdr-sim.exe`
  yoluna, sonra PATH'e bakıyor. Bu ayrı bir upstream proje
  (https://github.com/osqzss/gps-sdr-sim), bu repoya ait değil; derlenmesi gerekiyor.
  `C:\BACKUP` içinde de kopyası yok.
- `de5b421` commit mesajı "compile notes" diyor, ama commit sadece kodu değiştiriyor.
  Derleme notu hiçbir yerde yazılı değil.

## Yapılanlar

- **Erken "Done." (2026-09-24, `343a6bf`).** Eskiden `prog_q`'ya gelen `100` hem çubuğu
  dolduruyor hem de işi bitmiş sayıp butonu açıyordu. `gps-sdr-sim` hata verse bile "Done."
  kalıyordu. Kuyruk protokolü: `0–100` sadece çubuk, `("status", metin)` durum satırı;
  işi bitiren tek sinyal `PROG_DONE`, `PROG_FAIL` ya da `PROG_CANCEL`.
- **İptal (2026-09-25).** GUI ile worker arasında bir `Job` nesnesi: `cancel` olayı +
  çalışan `gps-sdr-sim` süreci. Cancel butonu `Job.stop()` çağırır: olayı kurar, süreci
  `terminate()` eder. İndirmede yarım `.gz`, simde yarım `.C8` silinir.
  Tuzak: worker thread daemon, pencere kapanınca ölür ama `gps-sdr-sim` ayrı süreç olduğu için
  1.5 GB yazmaya devam ederdi. Bu yüzden `WM_DELETE_WINDOW` iş sürerken onay ister, süreci
  durdurur, worker'ı en fazla 5 sn bekler (yarım dosyayı silsin diye).
  Sınır: indirme `iter_content` içinde veri beklerken takılırsa iptal bir sonraki parçada
  (en kötü 60 sn timeout) işler.
- **`.C8` boyutu.** `c8_size_bytes = sample_rate × duration × 2` (`-b 8`: I ve Q birer bayt).
  Sample rate'in yanında canlı tahmin; başlarken hedef diskte yer yoksa hata verir.
- **`.netrc`.** Açılışta `~/.netrc`, sonra `~/_netrc` okunur; `urs.earthdata.nasa.gov`
  kaydı varsa alanlar doldurulur. Parola hiçbir yere yazılmaz; sadece okuma.
- **PATH araması.** `resolve_exe()`: dosya yolu değilse `shutil.which()`. Eskiden
  `os.path.isfile()` yüzünden PATH'teki exe hiç bulunmuyordu. Exe yoksa artık indirme
  başlamadan hata veriyor (eskiden indirmeden sonra fark ediliyordu).
- **Test sırasında bulunan iki ek hata:**
  - `dict | None` gibi imzalar Python 3.8/3.9'da tanım anında `TypeError` verir; README
    "3.8+" diyor. `from __future__ import annotations` eklendi. 3.8 yorumlayıcısı makinede
    yok; sadece `ast.parse(feature_version=(3, 8))` ile sözdizimi doğrulandı.
  - GPS-SIM açılınca sample rate kutusu `state="normal"` olup serbest metin kabul ediyordu;
    listede olmayan değer `SAMPLE_RATES[...]` ile `KeyError` verirdi. Artık `readonly`.

## Test

Testler repoda değil, oturumun geçici klasöründeydi. Yaklaşım (yeniden yazmak için):
`EarthdataSession.get`'i sahte yanıtla, `brdc_downloader.subprocess.Popen`'ı `-o` yoluna
dosya yazan ve satır basan sahte süreçle değiştir; `download_worker`'ı doğrudan çağırıp
`prog_q`'daki bitiş sinyallerine bak. GUI için `BRDCApp()` + `withdraw()`, kuyruğa sinyal
koyup `_poll_queues()` çağır. 11 senaryo geçti: başarı, sim hatası, simsiz, iptal (indirme
ve sim sırasında), PATH, boyut, netrc (`_netrc`, başka host, bozuk dosya), GUI davranışı.
