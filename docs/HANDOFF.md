# HANDOFF

## Son durum (2026-09-24)

- Yerel `main` = `origin/main` = `eb7f917`. GitHub'da başka dal, PR, issue, release, fork yok.
  Repoda eksik dosya yok; GitHub'da olup burada olmayan bir şey bulunmadı.
- Bu dosya bu tarihte ilk kez oluşturuldu. Önceki oturumlardan yazılı devir notu yoktu.

## Bu makinenin durumu (repo dışı)

- ~~`requests` kurulu değil~~ → 2026-09-24'te kuruldu (requests 2.34.2, Python 3.13.15).
  `BRDC_Downloader.bat` ile uygulama açıldı, pencere geldi, `brdc_error.log` oluşmadı.
- **PATH tuzağı:** `WindowsApps\python3` (Microsoft Store yönlendiricisi) PATH'te Python313'ten
  önce geliyor. Git Bash'te `python` "Python was not found" diyor; tam yol kullan.
  `BRDC_Downloader.bat` `pythonw` çağırıyor; o Python313'ten geliyor ve çalışıyor.
- **`gps-sdr-sim.exe` yok.** Kod onu `..\gps-sdr-sim\gps-sdr-sim.exe` yolunda arıyor
  (`C:\Claude Projects\gps-sdr-sim\`), bulamazsa PATH'teki `gps-sdr-sim.exe`'ye düşüyor.
  Bu ayrı bir upstream proje (https://github.com/osqzss/gps-sdr-sim), bu repoya ait değil;
  derlenmesi gerekiyor. `C:\BACKUP` içinde de kopyası yok.
- `de5b421` commit mesajı "compile notes" diyor, ama commit sadece kodu değiştiriyor.
  Derleme notu hiçbir yerde yazılı değil.

## Yapılanlar

- **Erken "Done." düzeltildi (2026-09-24).** Eskiden `prog_q`'ya gelen `100` hem çubuğu
  dolduruyor hem de işi bitmiş sayıp butonu açıyordu; `gps-sdr-sim` daha çalışırken "Done."
  görünüyordu. Ayrıca `gps-sdr-sim` hata verse bile durum "Done." kalıyordu. Artık kuyruk
  protokolü: `0–100` sadece çubuk, `("status", metin)` durum satırı, işi bitiren tek sinyal
  `PROG_DONE` ya da `PROG_FAIL`. `gpssim_worker` artık `bool` döndürüyor; başarısızsa `PROG_FAIL`.
  Arayüzsüz testle doğrulandı (worker sinyal sırası + `_poll_queues` buton/durum davranışı);
  gerçek CDDIS indirmesi ve gerçek `gps-sdr-sim` ile denenmedi.

## Açık iyileştirmeler

1. ~~Erken "Done."~~ → yapıldı, yukarıda.
2. **İptal butonu yok.** `requests` stream döngüsüne ve `Popen`'a iptal bayrağı eklenebilir.
3. `.C8` tahmini boyut / disk alanı uyarısı (2.6 MHz × 300 sn ≈ 1.5 GB).
4. İsteğe bağlı: Earthdata kimlik bilgisini `~/.netrc`'ten okuma.
5. **PATH yedeği işe yaramıyor.** Yan klasörde exe yoksa varsayılan değer düz
   `gps-sdr-sim.exe` oluyor, ama `gpssim_worker` `os.path.isfile()` ile kontrol ettiği için
   PATH'teki exe asla bulunmuyor ("not found" hatası). `shutil.which()` ile çözülebilir.

Kaynak: `C:\Claude Projects\_shared\claude-verisi\C--Claude-Projects-brdc-downloader\97f8db4a-….jsonl`
(o oturum öneri listesiyle bitti, kod değişmedi).
