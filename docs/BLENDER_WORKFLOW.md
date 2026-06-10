# Blender Çalışma Rehberi — El/Kafa Soketleri ve Item Düzeltme

Hedef: **her (hayvan × item) çiftini BİR kez düzelt** → her el-item'ı + her
kafa-item'ı kombinasyonu otomatik doğru olur (10 el + 2 kafa düzeltmesi = 20
kombinasyon). Düzeltmeler dosyaya (`tools/rig/item_attach.json`) yazılır; app
bunları çalışma anında uygular.

---

## BÖLÜM A — Kafa soketi ekleme (hayvan başına 1 kez)

El soketi (`socket_r`) zaten var. Kafa için aynısını yapacaksın:

1. Blender'ı aç → `File > Import > glTF 2.0` →
   `D:\blenderprojects\gen\avatars_socketed\fox_socketed.glb` (avatarın socket'li hâli).
2. `Add > Empty > Plain Axes` (Shift+A).
3. Sağ panelde adını **tam olarak `socket_head`** yap (Outliner'da çift tıkla).
4. Empty'yi kafanın üstüne taşı (G ile taşı; şapkanın oturacağı nokta —
   genelde kafanın tepe-orta noktası, hafif önde).
5. Empty'yi gövdeye bağla: önce Empty'yi seç, sonra **Shift ile** gövde mesh'ini
   seç → `Ctrl+P > Object (Keep Transform)`.
6. `File > Export > glTF 2.0` → **aynı dosyanın üstüne** kaydet
   (`avatars_socketed\fox_socketed.glb`). Format: glTF Binary (.glb).
7. Diğer 6 hayvan için tekrarla (cat, deer, frog, panda, pinkcat, bear).

> Not: Empty'nin boyutu önemli değil (glTF korumuyor); yalnız **konumu ve adı**
> önemli. Konum = item'ın merkezinin geleceği yer.

Sonra sunucuda avatarları yeniden içe al:
```powershell
cd C:\Users\ishak\habitbud-backend\habit_tracker
venv\Scripts\python manage.py import_avatar_models --dir D:\blenderprojects\gen\avatars_socketed --thumbs-dir ..\habit_tracker\assets\animals_gemini_2d_v2 --replace
```

## BÖLÜM B — Bir item'ı bir hayvanda düzeltme (çift başına 1 kez)

1. Önce kaba birleşimleri üret (görsel başlangıç noktası):
   ```powershell
   tools\rig\attach_all.ps1 -Force        # el + kafa, tüm kombinasyonlar
   ```
2. Blender'da düzelteceğin çifti aç:
   `File > Import > glTF 2.0` → `D:\blenderprojects\gen\out\fox__magic_wand.glb`
3. Outliner'da **item objesini** seç (avatar gövdesi değil — genelde `geometry_0`
   adlı KÜÇÜK mesh; tıklayıp 3D görünümde hangisinin yandığına bak).
4. Item'ı yerine oturt:
   - `G` taşı (G sonra X/Y/Z eksen kilidi), `R` döndür, `S` ölçekle.
   - Elin tam kavradığı / kafaya tam oturduğu hâle getir.
5. **Scripting** sekmesine geç → `Open` → 
   `C:\Users\ishak\habitbud-backend\tools\rig\extract_offset.py`
6. Script'in üst kısmındaki iki satırı düzenle:
   ```python
   AVATAR = 'fox'          # hangi hayvan
   ITEM = 'magic_wand'     # hangi item (dosya adındaki slug)
   ```
7. Item objesi SEÇİLİYKEN **Run Script** (▶). Konsolda
   `saved fox/magic_wand: loc=... rot=... scale=...` görmelisin —
   düzeltme `tools/rig/item_attach.json` → `avatar_overrides`'a yazıldı.
8. Sıradaki çifte geç (aynı Blender oturumunda yeni dosya import edebilirsin).

## BÖLÜM C — Düzeltmeleri yayınlama (toplu, istediğin zaman)

```powershell
cd C:\Users\ishak\habitbud-backend\habit_tracker
venv\Scripts\python manage.py import_attach_tuning    # app'e servis edilir
cd .. ; tools\rig\attach_all.ps1 -Force               # (opsiyonel) bake'leri tazele
cd habit_tracker ; venv\Scripts\python manage.py import_combos --dir D:\blenderprojects\gen\out --clean
```
App, Avatar Studio'yu bir sonraki açışında düzeltmeleri kullanır
(`/users/api/attach-tuning/`). **Kombinasyon başına iş yok** — `fox/magic_wand`
düzeltmesi, fox'un kafasında ne olursa olsun geçerlidir.

## Yapılacaklar özeti

- [ ] 7 hayvana `socket_head` ekle + yeniden export (Bölüm A)
- [ ] `import_avatar_models --replace` çalıştır
- [ ] El item'ları: 7 hayvan × 6 item düzelt (Bölüm B) — yalnız bozuk duranları
- [ ] Kafa item'ları: 7 hayvan × 7 item düzelt — yalnız bozuk duranları
- [ ] `import_attach_tuning` ile yayınla (Bölüm C)

> İpucu: önce TEK çifti (fox + magic_wand) uçtan uca yap, app'te gör, sonra
> seri üretime geç.
