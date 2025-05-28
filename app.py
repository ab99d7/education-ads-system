from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'education_ads_secret_key_2025'

# إنشاء قاعدة البيانات والجداول
def init_db():
    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            department TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # جدول الإعلانات
    c.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            target_audience TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # إضافة بيانات تجريبية
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        # إضافة مستخدمين تجريبيين
        sample_users = [
            ('د. أحمد محمد', 'عميد', 'dean@university.edu', generate_password_hash('dean123'), 'إدارة الكلية', '0501234567'),
            ('د. فاطمة علي', 'رئيس قسم', 'head@university.edu', generate_password_hash('head123'), 'قسم علوم الحاسب', '0501234568'),
            ('أ. محمد سالم', 'معلم', 'teacher@university.edu', generate_password_hash('teacher123'), 'قسم الرياضيات', '0501234569'),
            ('سارة أحمد', 'طالب', 'student@university.edu', generate_password_hash('student123'), 'قسم علوم الحاسب', '0501234570')
        ]
        
        for user in sample_users:
            c.execute('INSERT INTO users (name, role, email, password, department, phone) VALUES (?, ?, ?, ?, ?, ?)', user)
    
    conn.commit()
    conn.close()

# تهيئة قاعدة البيانات عند بدء التطبيق
init_db()

# الصفحة الرئيسية
@app.route('/')
def home():
    return render_template('index.html')

# صفحة تسجيل الدخول
@app.route('/login')
def login_page():
    return render_template('login.html')

# معالجة تسجيل المستخدم الجديد
@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    role = request.form['role']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    department = request.form.get('department', '')
    phone = request.form.get('phone', '')

    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (name, role, email, password, department, phone) VALUES (?, ?, ?, ?, ?, ?)',
                  (name, role, email, password, department, phone))
        conn.commit()
        flash('تم تسجيل الحساب بنجاح!', 'success')
    except sqlite3.IntegrityError:
        flash('البريد الإلكتروني مستخدم بالفعل', 'error')
    conn.close()
    return redirect(url_for('home'))

# معالجة تسجيل الدخول
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()

    if user and check_password_hash(user[4], password):
        session['user'] = {
            'id': user[0], 
            'name': user[1], 
            'role': user[2], 
            'email': user[3],
            'department': user[5],
            'phone': user[6]
        }
        flash(f'مرحباً {user[1]}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('بيانات الدخول غير صحيحة', 'error')
        return redirect(url_for('login_page'))

# لوحة التحكم
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('يجب تسجيل الدخول أولاً', 'error')
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    
    # جلب المستخدمين حسب الصلاحية
    user_role = session['user']['role']
    if user_role == 'عميد':
        c.execute('SELECT id, name, role, email, department, phone FROM users ORDER BY role, name')
    elif user_role == 'رئيس قسم':
        c.execute('SELECT id, name, role, email, department, phone FROM users WHERE department = ? OR role = ?', 
                 (session['user']['department'], 'طالب'))
    else:
        c.execute('SELECT id, name, role, email, department, phone FROM users WHERE id = ?', 
                 (session['user']['id'],))
    
    users = c.fetchall()
    
    # جلب الإعلانات
    c.execute('''SELECT a.id, a.title, a.content, a.category, a.target_audience, 
                        u.name as creator, a.created_at, a.is_active
                 FROM ads a 
                 JOIN users u ON a.created_by = u.id 
                 ORDER BY a.created_at DESC''')
    ads = c.fetchall()
    
    conn.close()
    return render_template('dashboard.html', users=users, ads=ads, user=session['user'])

# إضافة إعلان جديد
@app.route('/add_ad', methods=['POST'])
def add_ad():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    title = request.form['title']
    content = request.form['content']
    category = request.form['category']
    target_audience = request.form['target_audience']
    
    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    c.execute('INSERT INTO ads (title, content, category, target_audience, created_by) VALUES (?, ?, ?, ?, ?)',
              (title, content, category, target_audience, session['user']['id']))
    conn.commit()
    conn.close()
    
    flash('تم إضافة الإعلان بنجاح!', 'success')
    return redirect(url_for('dashboard'))

# حذف إعلان
@app.route('/delete_ad/<int:ad_id>')
def delete_ad(ad_id):
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    
    # التحقق من الصلاحية
    user_role = session['user']['role']
    if user_role == 'عميد':
        c.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
    else:
        c.execute('DELETE FROM ads WHERE id = ? AND created_by = ?', (ad_id, session['user']['id']))
    
    conn.commit()
    conn.close()
    
    flash('تم حذف الإعلان بنجاح!', 'success')
    return redirect(url_for('dashboard'))

# إدارة المستخدمين
@app.route('/users')
def users_management():
    if 'user' not in session or session['user']['role'] not in ['عميد', 'رئيس قسم']:
        flash('ليس لديك صلاحية للوصول لهذه الصفحة', 'error')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    c.execute('SELECT id, name, role, email, department, phone, created_at FROM users ORDER BY role, name')
    users = c.fetchall()
    conn.close()
    
    return render_template('users_management.html', users=users, user=session['user'])

# حذف مستخدم
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user' not in session or session['user']['role'] != 'عميد':
        flash('ليس لديك صلاحية لحذف المستخدمين', 'error')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    flash('تم حذف المستخدم بنجاح!', 'success')
    return redirect(url_for('users_management'))

# تسجيل الخروج
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('home'))

# API للحصول على إحصائيات
@app.route('/api/stats')
def get_stats():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = sqlite3.connect('education_system.db')
    c = conn.cursor()
    
    # إحصائيات المستخدمين
    c.execute('SELECT role, COUNT(*) FROM users GROUP BY role')
    user_stats = dict(c.fetchall())
    
    # إحصائيات الإعلانات
    c.execute('SELECT category, COUNT(*) FROM ads GROUP BY category')
    ad_stats = dict(c.fetchall())
    
    # إجمالي الإعلانات
    c.execute('SELECT COUNT(*) FROM ads WHERE is_active = 1')
    total_ads = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'user_stats': user_stats,
        'ad_stats': ad_stats,
        'total_ads': total_ads
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)