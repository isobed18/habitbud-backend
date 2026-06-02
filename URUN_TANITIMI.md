# HabitBud 🌱 - Ürün Tanıtımı ve Teknik Raporu

HabitBud; **Snapchat tarzı görsel doğrulamalı check-in'ler** ile **Duolingo tarzı dopamin ve oyunlaştırma döngülerini** bir araya getiren sosyal bir alışkanlık takip platformudur. Bu rapor; uygulamanın 3B karakter (avatar) entegrasyonu, kişiselleştirme (item) mağazası, başarımlar (rozet), dopamin mekanikleri ve hem frontend hem de backend tarafındaki gelişmiş görsel efektler/animasyonları detaylandırmaktadır.

---

## 🌟 1. Genel Bakış ve Mimari Yapı

HabitBud, kullanıcıların sadece tek bir tıkla alışkanlıklarını tamamlamak yerine, arkadaşlarıyla veya grup odalarında **fotoğraflı kanıtlar** paylaşarak sosyal denetim altında alışkanlık edinmelerini sağlar.

- **Frontend**: React Native (Expo Go) + Three.js & React Three Fiber (R3F) + Lottie + React Native Reanimated.
- **Backend**: Django (5.1) + Django REST Framework + Django Channels (ASGI real-time WebSockets) + SQLite.
- **3B Avatar Üretim Hattı**: Tencent Hunyuan3D-2 modeli kullanılarak 2D hayvan görsellerinden otomatik düşük poligonlu 3B GLB modelleri oluşturulmuştur.

---

## 🐻 2. 3B Avatar ve Akıllı Giydirme (Item) Sistemi

Sistemin kalbinde, her kullanıcının profilinde yer alan ve 3B olarak incelenebilen sevimli maskot karakterler yer alır.

### A. Hunyuan3D-2 3B Model Üretim Hattı
- 2D temiz arka planlı hayvan görselleri (`animals_gemini_2d_v2`) Hunyuan3D-2 pipeline'ı üzerinden geçirilerek 3B GLB mesh modellerine dönüştürülmüştür.
- Üretilen modeller: **Ayı (2 adet), Kedi, Tavşan, Panda, Pembe Kedi, Kurbağa, Tilki, Geyik.**
- Modeller backend veritabanına `import_avatar_models` komutuyla `AvatarModel` olarak aktarılmış, isimleri, ölçekleri (`scale`) ve emojileriyle eşleştirilmiştir.

### B. Akıllı 3B Görüntüleyici ve Shaders (WebGL)
- **Plushify Algoritması (`Avatar3D.js`)**: Hunyuan GLB modellerinin metalik/yansımasız yapısından ötürü karanlık görünmesini önlemek için, model yüklendiğinde tüm mesh'lerin metalik değeri 0'a çekilmekte, pürüzlülüğü 0.85'e ayarlanmakta ve normal haritaları (vertex normals) yeniden hesaplanarak yumuşak "kadifemsi/plushy" bir görünüm elde edilmektedir.
- **İnertial Döndürme Kontrolü**: Drag-to-rotate mekanizması, parmak bırakıldığında aniden durmaz; fırlatma hızına (`vy`) göre sönümlenerek yumuşak bir şekilde dönmeye devam eder (sönümleme çarpanı `0.94`).
- **Canlı Idle Animasyonları**: Karakterler hareketsiz durmaz:
  - **Nefes Alma Animasyonu**: `Math.sin(t * 2.1) * 0.018` oranında scale/boyut dalgalanması.
  - **Zıplama Animasyonu**: `Math.sin(t * 2.4) * 0.025` oranında dikey eksende (y-axis) sallanma.
  - **Doğal Kafa Eğme**: `Math.sin(t * 1.35) * 0.045` ile yanlara yatış ve `Math.sin(t * 1.6) * 0.018` ile öne-arkaya eğilme.

### C. Soket/Bağlantı Noktası Bazlı Giydirme (Item Attachment)
Modeller rigged (iskeletli) olmak yerine, **MVP standardına uygun olarak akıllı bağlantı noktaları (Anchors)** ile giydirilir. Alınan giysiler/aksesuarlar, karakterlerin lokal koordinatlarındaki şu noktalara yerleştirilir:
- **Head (Baş)**: Kulaklık, Şapka, Bere, Taç, Crystal Bottle vb. `[0, 1.05, 0.15]`
- **Face (Yüz)**: Güneş Gözlüğü, Yuvarlak Gözlük, Maske vb. `[0, 0.68, 0.6]`
- **Hand (El)**: Dambıl, Su Şişesi, Kahve, Sihirli Değnek, Kitap, Balon vb. `[0.7, 0.05, 0.4]`
- **Back (Sırt)**: Sırt çantası veya kanat aparatları. `[0, 0.45, -0.55]`
- **Neck (Boyun)**: Kolye, atkı vb. `[0, 0.5, 0.4]`

*Kurallar gereği her bağlantı noktasına aynı anda sadece bir item giyilebilir.*

---

## 💎 3. Oyunlaştırma (Gamification) ve Mağaza

Alışkanlıkları sürdürülebilir kılmak için Duolingo esintili ödül ve cüzdan sistemi kurulmuştur.

### A. XP ve Elmas (Gems) Ayrımı
Eski versiyonlarda aynı görünen XP ve Elmas sistemleri tamamen birbirinden ayrılmıştır:
1. **XP (⚡)**: Karakterin seviyesini belirler. Alışkanlık check-in'i onaylandığında veya arkadaş onayı verildiğinde kazanılır.
2. **Elmas (💎 - Points)**: Uygulama içi mağazada harcanabilen premium para birimidir. Zor kazanılır; seviye atlama ödülleri (`Seviye * 5` formülüyle) ve tamamlanan büyük meydan okumalardan (Challenges) elde edilir.

### B. Alışkanlık Mağazası (Store) ve Seri Dondurucu (Streak Freeze)
- **Seri Dondurucu (❄️)**: Kullanıcılar 20 Elmas karşılığında mağazadan Seri Dondurucu satın alabilirler.
- **Otomatik Koruma**: Eğer kullanıcı gün içerisinde bir alışkanlığı yapmayı kaçırırsa, backend tarafındaki cron mekanizması (`check_and_apply_streak_freeze`) kullanıcının envanterindeki bir dondurucuyu eksilterek alışkanlık ve arkadaşlık serisinin (streaks) sıfırlanmasını otomatik olarak engeller ve kullanıcıya WebSocket/Push üzerinden bildirim gönderir.

---

## 🎖️ 4. Görevler (Challenges) ve Rozetler (Achievements)

Sistemde solo veya duo (arkadaşlarla ortaklaşa) katılabilecek meydan okuma şablonları bulunur:

### A. Görev Şablonları (Templates)
1. **30 Day Runner (Solo)**: 30 gün boyunca koşu alışkanlığı tamamlama. Ödül: `500 XP, 500 Elmas + Golden Shoes (Epic Item)`.
2. **7 Day Water Warrior (Solo)**: 7 gün su içme alışkanlığı. Ödül: `100 XP, 100 Elmas + Crystal Bottle (Rare Item)`.
3. **7 Day Productivity Duo (Duo)**: Arkadaşınla 7 gün verimli çalışma. Ödül: `150 XP, 150 Elmas + Keyboard of Wisdom (Epic Item)`.
4. **30 Day Study Buddy (Duo)**: 30 gün ders çalışma. Ödül: `1000 XP, 1000 Elmas + Heart Locket (Legendary Item)`.
5. **30 Day Gym Rats (Duo)**: 30 gün spor salonu. Ödül: `1200 XP, 1200 Elmas + Golden Shoes (Epic Item)`.

### B. Başarımlar ve Rozet Ekranı (`Achievements.js`)
Görevler tamamlandığında kullanıcılara kalıcı rozetler verilir. Frontend'deki Başarımlar ekranında bu rozetler tipine göre akıllıca gruplanır ve ikon eşleşmesi yapılır:
- `challenge` -> 🏆 Kupa ikonu
- `streak` -> 🔥 Ateş ikonu
- `social` -> 👥 İnsanlar ikonu
- `habit` -> 🍃 Yaprak ikonu

---

## 📸 5. Sosyal Etkileşim ve Snapchat Tarzı "Checks"

Uygulamanın ana akışı tamamen görsel paylaşıma dayanır.

### A. Fotoğraflı Check-in ve Hikayeler
- **SubmitProof Ekranı**: Kullanıcılar kamera veya galeriden alışkanlık kanıtı (proof) yükler. Bunu ister 24 saatlik geçici Hikayelerinde paylaşırlar, ister arkadaşlarına doğrudan mesaj olarak gönderirler.
- **Geri Al (Undo) Mekanizması**: Yanlışlıkla gönderilen veya hikayeye eklenen bir kanıtı geri çekmek için **4.5 saniyelik bir geri alma penceresi** bulunur. Ekranda görsel bir countdown bar akar; "Geri Al" butonuna basılırsa kanıtlar anında silinir.

### B. Mesajlaşma (Chat.js)
- Modern Instagram/Snapchat tarzı sohbet ekranı.
- Karşı tarafın mesaj balonunun yanındaki avatarına veya sohbet başlığına tıklandığında doğrudan profil penceresi açılır.

---

## 🎨 6. Gelişmiş Görsel Efektler ve Animasyonlar

HabitBud premium hissi uyandırmak amacıyla mikro-animasyonlar ve zengin efektler ile doldurulmuştur:

### A. Küresel Kutlama Konfeti Patlaması
- Önemli bir görev tamamlandığında, seviye atlandığında veya mağazadan dondurucu alındığında ekranda tam ekran Lottie konfeti animasyonu (`confetti.json`) oynatılır.

### B. Uçan Ödül Kartları (Floating Chips)
- Kullanıcı ödül aldığında ekranın sağ alt tarafında `+15 XP` veya `+5 💎` şeklinde renkli çipler belirir.
- **XP Çipi (Mavi/Amber)**: 59,130,246 renk kodlu yumuşak mavi gölgeli kart.
- **Elmas Çipi (Cyan)**: 6,182,212 renk kodlu parlak neon cyan gölgeli kart.
- Bu kartlar React Native spring (yay) fiziğiyle içeri fırlatılır, yukarı doğru süzülür ve sönümlenerek kaybolur.

### C. Pulsing Toplam Göstergeleri
- Ödül çiplerinin yükselip yok olmasının ardından, sağ altta bulunan birikmiş XP (`⚡`) ve Elmas (`💎`) sayaçları aldıkları puan kadar büyür (`scale: 1.25` yay efektiyle şişip geri sönerek) ve kullanıcının dopamin eşiğini tetikler.

### D. Tetikleyici Lottie Efektleri
Geliştirme kapsamında entegre edilen özel Lottie animasyonları şunlardır:
1. `success.json`: Alışkanlık tamamlandığında beliren yeşil onay işareti.
2. `fire.json`: Seriyi gösteren canlı ve yanan alev halkası.
3. `trophy_unlock.json`: Görevler bitince kupanın parlayarak dönmesi.
4. `badge_unlock.json`: Kazanılan madalyanın ışıltılı kilidi.
5. `diamond.json` / `gem.json`: Satın alım ve elmas kazanımlarında elmasın parlaması.
6. `xp_star_blue.json`: XP kazanıldığında mavi yıldız patlaması.

### E. Dokunsal Geri Bildirimler (Haptics)
- `light`: Sayaç arttırılırken hafif titreşim.
- `medium`: Kamera açılırken veya paylaşım listesi açılırken orta şiddette titreşim.
- `success`: İşlem başarıyla kaydedildiğinde zafer titreşimi.
- `error`: Kaydetme hatası alındığında hata titreşimi.
- `selection`: Avatar veya eşya seçerken tıklama hissi veren hafif dokunsal bildirim.

---

## 🛠️ 7. Backend & Yönetim Komutları

Sistemi beslemek ve yönetmek için backend tarafında özel CLI komutları yer almaktadır:
- `python manage.py import_avatar_models --dir <yol> --scale 1.0`: Hunyuan3D-2'den çıkan tüm GLB dosyalarını topluca sisteme import eder.
- `python manage.py populate_challenges`: Solo/Duo görev şablonlarını ve özel envanter ödüllerini veritabanına işler.
- `python manage.py seed_habit_templates`: Su İç, Kitap Oku, Kitap vb. hazır şablonları yükler.
- `python manage.py send_check_reminders`: Alışkanlık hatırlatıcılarını gönderir ve akşam serisi riske girenleri uyarır.
- `python manage.py reset_db`: Veritabanını sıfırlayıp tüm migrations ve seed işlemlerini tek seferde yapar.

HabitBud, yenilenen 3B görsel altyapısı ve dopamin odaklı animasyonlarıyla tamamen yayına hazır hale getirilmiştir.
