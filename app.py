from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key

# Initialize the database if it doesn't exist
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if the Users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Users'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Run schema.sql if the Users table does not exist
        with open('schema.sql') as f:
            conn.executescript(f.read())
        print("Database initialized.")
    else:
        print("Database already initialized.")
    
    conn.close()

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Call init_db directly when starting the app
init_db()

# Route for the root URL, redirects to login
@app.route('/')
def index():
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print (password," - ")
        role = request.form['role']

        print(f"Username: {username}, Role: {role}")

        # Connect to the database and check credentials
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND role = ?', (username, role)).fetchone()
        conn.close()

        if user:
            print("User found in database.")
            print(user['password'])
            if (user['password']== password):
                print("Password match.")
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                return redirect(url_for('dashboard'))
            else:
                print("Password does not match.")
        else:
            print("User not found in database.")

        flash('Invalid credentials. Please try again.')
    return render_template('login.html')

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    return render_template('dashboard.html', role=role)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login')) 

if __name__ == '__main__':
    app.run(debug=True)
