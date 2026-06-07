1. Masuk ke Folder Proyek
Buka terminal/Command Prompt, lalu arahkan ke folder tempat proyek Anda berada:
Bash:
cd path/ke/folder/hitung_semangka

2. Buat Virtual Environment
Buat lingkungan virtual baru bernama venv agar instalasi tidak mengganggu sistem komputer:
Bash:
python -m venv venv

3. Aktifkan Virtual Environment
Jalankan perintah ini sesuai dengan sistem operasi komputer baru Anda:

Pengguna Windows:
Bash:
venv\Scripts\activate

Pengguna Mac/Linux:
Bash:
source venv/bin/activate

===KemudianMasuk Ke Folder "hitung_semangka"
Bash:
cd hitung_semangka

4. Instal Semua Dependencies
Baca file requirements.txt dan biarkan sistem menginstal semuanya secara otomatis:
Bash:
pip install -r requirements.txt

5. Bangun Ulang Database
Buat tabel-tabel yang dibutuhkan oleh Django dan library lainnya (seperti akun allauth):
Bash:
python manage.py migrate

6. Jalankan Server
Nyalakan aplikasi Anda:
Bash:
python manage.py runserver
