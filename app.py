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

def get_customer_bills(customer_id):
    conn = get_db_connection()
    bills = conn.execute('SELECT * FROM Bills WHERE customer_id = ?', (customer_id,)).fetchall()
    conn.close()
    return bills


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

@app.route('/bills')
def bills():
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))
    
    customer_id = session['user_id']
    bills = get_customer_bills(customer_id)
    print(bills,"<--")
    
    return render_template('bills.html', bills=bills)

@app.route('/register_customer', methods=['GET', 'POST'])
def register_customer():
    if 'user_id' not in session or session['role'] != 'officer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Collect customer details from the form
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        contact_info = request.form['contact_info']
        sector_no = request.form['sector_no']  # Example additional data
        connections = request.form['connections']
        reservoir_id = request.form['reservoir_id'] 

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the customer into the Users table
        cursor.execute(
            'INSERT INTO Users (username, password, role, name, contact_info) VALUES (?, ?, ?, ?, ?)',
            (username, password, 'customer', name, contact_info)
        )
        conn.commit()

        # Get the new user's ID
        user_id = cursor.lastrowid

        # Insert the customer details into the Customer table with the new user_id
        cursor.execute(
            'INSERT INTO Customer (userid, name, sector_no, connections, reservoir_id) VALUES (?, ?, ?,?,?)',
            (user_id, name, sector_no,connections, reservoir_id)
        )
        conn.commit()
        conn.close()

        flash('Customer registered successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('register_customer.html')



@app.route('/register_officer', methods=['GET', 'POST'])
def register_officer():
    # Check if the logged-in user is an admin
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Collect officer details from the form
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        contact_info = request.form['contact_info']
        sector_no = request.form['sector_no']  # Additional information for officer

        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the officer into the Users table
        cursor.execute(
            'INSERT INTO Users (username, password, role, name, contact_info) VALUES (?, ?, ?, ?, ?)',
            (username, password, 'officer', name, contact_info)
        )
        conn.commit()

        # Get the new user's ID
        user_id = cursor.lastrowid

        # Insert the officer details into the Officer table
        cursor.execute(
            'INSERT INTO Officer (officer_id, name, sector_no) VALUES (?, ?, ?)',
            (user_id, name, sector_no)
        )
        conn.commit()
        conn.close()

        flash('Officer registered successfully!')
        return redirect(url_for('dashboard'))
    
    return render_template('register_officer.html')


@app.route('/meter_reading/<int:customer_id>', methods=['GET', 'POST'])
def meter_reading(customer_id):
    if 'user_id' not in session or session['role'] != 'officer':
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Collect meter readings from the form
        reading = float(request.form['reading'])
        reading_date = request.form['reading_date']
        
        # Insert the reading into the database (you may want to create a Meter_Readings table for this)
        conn = get_db_connection()
        conn.execute('INSERT INTO Meter_Readings (customer_id, reading, reading_date) VALUES (?, ?, ?)',
                     (customer_id, reading, reading_date))
        conn.commit()

        # Calculate the bill based on the reading (this could be more complex in real applications)
        bill_amount = calculate_bill(reading)

        # Create a new bill for the customer
        conn.execute('INSERT INTO Bills (customer_id, bill_date, amount_due, due_date) VALUES (?, ?, ?, ?)',
                     (customer_id, reading_date, bill_amount, '2024-12-01'))  # Example due date
        conn.commit()
        conn.close()

        flash('Meter reading and bill created successfully!')
        return redirect(url_for('bills'))

    return render_template('meter_reading.html', customer_id=customer_id)

def calculate_bill(reading):
    # Simple calculation for demonstration: you can adjust the logic as needed
    base_rate = 10  # Example rate per unit
    return reading * base_rate



# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login')) 

if __name__ == '__main__':
    app.run(debug=True)
