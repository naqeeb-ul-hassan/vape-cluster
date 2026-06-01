# Vape Cluster - Django Backend Integration Guide 🚀

Assalam-o-Alaikum! Ye aapka Vape Cluster project ka complete Django backend integration hai. Humne frontend ko EXACTLY same rakha hai aur backend ko monolithic structure mein convert kar diya hai.

---

## 🛠️ Project Setup Instructions

### 1. Requirements Installation
Pehle saari zaroori libraries install karein:
```bash
pip install -r requirements.txt
```

### 2. Environment Variables (.env)
Humne `.env` file banayi hai jisme saari sensitive details hain. Aap isme apne MySQL credentials aur PayFast keys add kar sakte hain.
- `DB_NAME`: vape_cluster_db
- `DB_USER`: root (ya jo aapka user ho)
- `DB_PASSWORD`: (aapka password)

### 3. Database Connection
MySQL database create karein:
```sql
CREATE DATABASE vape_cluster_db;
```
Phir migrations run karein:
```bash
python manage.py makemigrations core
python manage.py migrate
```

### 4. Running the Project
Project start karne ke liye ye command chalayein:
```bash
python manage.py runserver
```
Website `http://127.0.0.1:8000/` par chal jayegi.

---

## 📁 Folder Structure (Asaan Samjhne ke Liye)

- **django_backend/**: Main project folder.
  - **core/**: Saara logic yahan hai (Models, Views, Urls).
  - **templates/**: Saari HTML files yahan hain.
    - `base.html`: Main layout (Header/Footer).
    - `index.html`: Home page.
    - `login-signup.html`: Auth page.
    - `admin/`: Dashboard files.
  - **static/**: CSS, JS, aur Images.
  - **media/**: User ke upload kiye huye products/blogs ki images.

---

## 🔐 Authentication System (Login/Signup)

- **Signup**: User email aur password se register kar sakta hai.
- **Login**: Successful login ke baad user direct **Admin Dashboard** par jayega.
- **Logout**: Logout karne par user wapis home page par redirect ho jayega.
- **Security**: Humne CSRF protection aur session handling use ki hai.

---

## 💳 PayFast Payment Integration

Humne `core/payment.py` aur `signals.py` mein PayFast ka structure ready kar diya hai. 
- **EasyPaisa / JazzCash / Card**: In sabke liye placeholder areas marked hain.
- **Security**: Duplicate payments se bachne ke liye transaction verification logic add kiya hai.

---

## 🖥️ Admin Dashboard (Custom Design)

Frontend ka admin panel ab backend se connected hai.
- **Dynamic Updates**: Agar aap admin panel se product change karenge, to wo website par foran update ho jayega.
- **Stats**: Dashboard par total orders, revenue, aur users ke stats real-time load honge.

---

## ⚠️ Important Notes (Carefully Parhein)

1. **Static Files**: Agar images load na hon, to `python manage.py collectstatic` run karein.
2. **Media Path**: Product images `media/products/` folder mein save hongi.
3. **MySQL Access**: Agar database connect na ho, to check karein ke MySQL service chal rahi hai aur credentials correct hain.
4. **CKEditor**: Blog posts ke liye rich text editor configure kiya gaya hai.

Shukriya! Agar koi masla ho to sir se discuss kar sakte hain, code bohat simple aur beginner-friendly rakha gaya hai. 😊