import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # In production, use a secure random key
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB max upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('ecommerce.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            contact TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            contact TEXT NOT NULL,
            image_filename TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        name = request.form['name']
        contact = request.form['contact']

        if not user_id or not password or not name or not contact:
            flash('All fields are required!', 'error')
        else:
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO users (user_id, password, name, contact) VALUES (?, ?, ?, ?)',
                             (user_id, password, name, contact))
                conn.commit()
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash(f'User ID {user_id} is already registered.', 'error')
            finally:
                conn.close()

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE user_id = ? AND password = ?', (user_id, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid User ID or Password.', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/add_product', methods=('GET', 'POST'))
@login_required
def add_product():
    if request.method == 'POST':
        category = request.form['category']
        name = request.form['name']
        price = request.form['price']
        contact = request.form['contact']
        
        # Check if the post request has the file part
        if 'image' not in request.files:
            flash('No image part', 'error')
            return redirect(request.url)
        file = request.files['image']
        
        # If user does not select file, browser also submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Save product to database
            conn = get_db_connection()
            conn.execute('INSERT INTO products (category, name, price, contact, image_filename) VALUES (?, ?, ?, ?, ?)',
                         (category, name, price, contact, filename))
            conn.commit()
            conn.close()
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Allowed image types are -> png, jpg, jpeg, gif, webp', 'error')

    return render_template('add_product.html')

@app.route('/delete_product/<int:id>', methods=('POST',))
@login_required
def delete_product(id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if product:
        # Delete image file if it exists
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image_filename'])
        if os.path.exists(image_path):
            os.remove(image_path)
        
        conn.execute('DELETE FROM products WHERE id = ?', (id,))
        conn.commit()
        flash('Product deleted!', 'success')
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Run the Flask development server
    app.run(debug=True, port=5000)
