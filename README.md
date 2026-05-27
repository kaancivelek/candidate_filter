# Intelligent Cloud HR - Candidate Filtering System

Bu proje, İnsan Kaynakları (HR) departmanları için geliştirilmiş, Yapay Zeka (AI) destekli bir CV ayrıştırma ve aday eşleştirme sistemidir. Sistem, yüklenen PDF/DOCX formatındaki özgeçmişleri analiz eder (spaCy & Tesseract kullanarak) ve iş ilanındaki gereksinimlerle karşılaştırarak bir "Eşleşme Skoru" (Match Score) üretir.

---

## 🚀 Gereksinimler (Prerequisites)

Projeyi bilgisayarınızda çalıştırmadan önce aşağıdakilerin kurulu olduğundan emin olun:

1. **Python 3.10** veya üzeri.
2. **Git** (Projeyi klonlamak için).
3. **Tesseract-OCR**: CV'lerdeki resim tabanlı metinleri okumak için zorunludur.
   - Windows kullanıcıları [buradan](https://github.com/UB-Mannheim/tesseract/wiki) indirip kurabilir.
   - Kurulumdan sonra `C:\Program Files\Tesseract-OCR\tesseract.exe` yolunun `parsing/utils/pdf2text.py` dosyası içindeki yolla eşleştiğini kontrol edin.
4. **PostgreSQL** (Sadece veritabanını test etmek isterseniz, aksi halde proje yerel ortamda varsayılan olarak SQLite kullanacaktır).

---

## 🛠️ Kurulum Adımları (Setup Instructions)

Projeyi kendi yerel bilgisayarınızda (Localhost) çalıştırmak için aşağıdaki adımları sırasıyla uygulayın:

### 1. Projeyi Klonlayın
```bash
git clone <GITHUB_REPO_URL_BURAYA_GELECEK>
cd candidate_filter
```

### 2. Sanal Ortam (Virtual Environment) Oluşturun ve Aktif Edin
Sistem kütüphanelerinizin karışmaması için sanal ortam kullanmanız zorunludur.

**Windows için:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux için:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Gerekli Kütüphaneleri Yükleyin
Proje için gerekli olan tüm kütüphaneleri (Django, spaCy, psycopg2 vb.) yükleyin:
```bash
pip install -r requirements.txt
```

### 4. Yapay Zeka (AI) Dil Modelini İndirin
Sistemin CV'leri anlayabilmesi için İngilizce NLP modelini indirmesi gerekmektedir. (Bu komutu çalıştırmazsanız proje hata verir):
```bash
python -m spacy download en_core_web_sm
```

### 5. Çevre Değişkenlerini (.env) Ayarlayın
Güvenlik nedeniyle şifreler ve API anahtarları GitHub'a yüklenmez. Projenin ana dizininde (`manage.py` ile aynı seviyede) `.env` adında yeni bir dosya oluşturun ve içine şu bilgileri ekleyin:

```env
SECRET_KEY=buraya_rastgele_uzun_bir_sifre_yazin_ornek_12345!@#
EMAIL_HOST_USER=sirket_emailiniz@gmail.com
EMAIL_HOST_PASSWORD=gmail_uygulama_sifresi
```
*(Not: `EMAIL_HOST_PASSWORD` için kendi Gmail şifrenizi DEĞİL, Google hesabınızdan alacağınız 16 haneli "Uygulama Şifresini" kullanmalısınız. Şifre sıfırlama maillerinin çalışması için bu gereklidir).*

### 6. Veritabanını Oluşturun (Migrations)
Sistem yerel ortamda (Local) otomatik olarak SQLite kullanacak şekilde ayarlanmıştır. Tabloları oluşturmak için:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Admin (Süper Kullanıcı) Hesabı Oluşturun
Sisteme giriş yapabilmek için ilk İK yöneticisi hesabını oluşturun:
```bash
python manage.py createsuperuser
```
*(Sizden e-posta, kullanıcı adı ve şifre isteyecektir).*

### 8. Sunucuyu Başlatın
Tebrikler! Kurulum bitti. Artık sunucuyu başlatabilirsiniz:
```bash
python manage.py runserver
```

Tarayıcınızı açın ve `http://127.0.0.1:8000` adresine giderek oluşturduğunuz admin hesabı ile sisteme giriş yapın.

---

## 💡 Ekip İçin Önemli Notlar ve Mimariler

* **Veritabanı Yapısı:** `settings.py` dosyası akıllı bir yapıya sahiptir. Kod yerel bilgisayarınızda çalışırken `db.sqlite3` kullanır. Ancak proje Railway veya benzeri bir bulut sunucuya yüklendiğinde (`DATABASE_URL` değişkeni algılandığında) otomatik olarak **PostgreSQL** veritabanına geçiş yapar. Sizin yerel kodunuzda değişiklik yapmanıza gerek yoktur.
* **Medya Dosyaları:** Sisteme test amaçlı CV yüklediğinizde, dosyalar `media/` klasörüne kaydedilecektir. Veri gizliliğini korumak amacıyla bu klasör `.gitignore` içine eklenmiştir ve GitHub'a yüklenmeyecektir.
* **Yetenek Havuzu (Skills DB):** Özgeçmiş ayrıştırma (Parsing) işlemi sırasında kullanılan kelime havuzu `parsing/utils/skills_db.txt` dosyasında bulunur. Sistemin yeni teknolojileri (örneğin yeni bir programlama dili) tanımasını isterseniz, bu dosyaya yeni kelimeler ekleyebilirsiniz.
* **Parola Sıfırlama (Password Reset):** Şifremi unuttum özelliği SMTP (Gmail) kullanılarak ayarlanmıştır. Eğer yerel ortamda `.env` dosyanıza doğru mail bilgilerini girmezseniz bu özellik çalışmayacaktır.