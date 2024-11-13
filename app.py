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

def get_meter_readings(customer_id):
    conn = get_db_connection()
    readings = conn.execute('SELECT * FROM MeterReadings WHERE customer_id = ?', (customer_id,)).fetchall()
    conn.close()
    return readings


# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def calculate_bill(customer_id, new_reading):
    conn = get_db_connection()
    
    # Get the last meter reading for this customer
    last_reading_data = conn.execute('''
        SELECT meter_reading, reading_date 
        FROM MeterReadings 
        WHERE customer_id = ? 
        ORDER BY reading_date DESC 
        LIMIT 1 OFFSET 1
    ''', (customer_id,)).fetchone()
    
    # Get customer connections and other relevant information
    customer_data = conn.execute('''
        SELECT connections 
        FROM Customer 
        WHERE customer_id = ?
    ''', (customer_id,)).fetchone()
    
    conn.close()

    # Base rate and multiplier (you can customize these)
    base_rate = 0.05  # rate per liter
    connection_multiplier = 1 + (0.1 * customer_data['connections'])  # increase based on number of connections

    # Calculate consumption
    if last_reading_data:
        previous_reading = last_reading_data['meter_reading']
        consumption = new_reading - previous_reading
    else:
        # First reading, assume zero previous consumption
        consumption = new_reading

    # Calculate bill amount
    bill_amount = consumption * base_rate * connection_multiplier
    return bill_amount


# Call init_db directly when starting the app
init_db()

# Route for the root URL, redirects to login
@app.route('/')
def index():
    return redirect(url_for('login'))

#login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Connect to the database and check credentials
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ? AND role = ?', (username, role)).fetchone()

        if user and (user['password']== password):
            # Store basic user info in the session
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']

            if role == 'officer':
        # Fetch and store sector_no for officer using a nested query
                officer = conn.execute('''
                    SELECT sector_no 
                    FROM Officer 
                    WHERE name = (
                        SELECT name 
                        FROM Users 
                        WHERE user_id = ?
                    )
                ''', (user['user_id'],)).fetchone()
                session['sector_no'] = officer['sector_no'] if officer else None

            elif role == 'customer':
        # Retrieve and store customer_id for customer using a join
                customer = conn.execute('''
                    SELECT Customer.customer_id 
                    FROM Customer 
                    JOIN Users ON Customer.userid = Users.user_id 
                    WHERE Users.user_id = ?
                ''', (user['user_id'],)).fetchone()
                session['customer_id'] = customer['customer_id'] if customer else None


            conn.close()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.')
            conn.close()
    return render_template('login.html')



# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session.get('role')
    return render_template('dashboard.html', role=role)


@app.route('/register_customer', methods=['GET', 'POST'])
def register_customer():
    if 'user_id' not in session or session['role'] != 'officer':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        contact_info = request.form['contact_info']
        sector_no = request.form['sector_no']
        reservoir_id = request.form['reservoir_id']
        connections = request.form['connections']
        
        conn = get_db_connection()
        
        # Check if username is unique
        existing_user = conn.execute('SELECT * FROM Users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            flash("Username already taken. Please choose another one.")
            conn.close()
            return render_template('register_customer.html')
        
        # Validate password (minimum 8 characters, includes letters and numbers)
        if len(password) < 8 or not any(char.isdigit() for char in password) or not any(char.isalpha() for char in password):
            flash("Password must be at least 8 characters long and include both letters and numbers.")
            conn.close()
            return render_template('register_customer.html')
        
        # Validate contact info (basic check for phone number or email)
        if not (contact_info.isdigit() and len(contact_info) >= 10) and "@" not in contact_info:
            flash("Invalid contact information. Provide a valid phone number or email.")
            conn.close()
            return render_template('register_customer.html')

        # Check connections (must be a positive integer)
        try:
            connections = int(connections)
            if connections <= 0:
                raise ValueError
        except ValueError:
            flash("Connections must be a positive integer.")
            conn.close()
            return render_template('register_customer.html')
                
        # Insert into Users table
        conn.execute('INSERT INTO Users (username, password, role, name, contact_info) VALUES (?,?, ?, ?, ?)',
                     (username, password, 'customer', name, contact_info))
        user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # Insert into Customer table
        conn.execute('INSERT INTO Customer (name, sector_no,  reservoir_id, connections, userid) VALUES (?, ?, ?, ?, ?)',
                     (name, sector_no, reservoir_id, connections, user_id))
        
        conn.commit()
        conn.close()
        
        flash("Customer registered successfully.")
        return redirect(url_for('dashboard'))
    
    return render_template('register_customer.html')

@app.route('/meter_readings')
def meter_readings():
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))

    customer_id = session.get('customer_id')  # Make sure customer_id is stored in session upon login
    readings = get_meter_readings(customer_id)
    
    return render_template('meter_readings.html', readings=readings)


@app.route('/register_officer', methods=['GET', 'POST'])
def register_officer():
    # Ensure only admins can access this route
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        sector_no = request.form['sector_no']
        
        conn = get_db_connection()
        
        # Check if username is unique
        existing_user = conn.execute('SELECT * FROM Users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            flash("Username already taken. Please choose another one.")
            conn.close()
            return render_template('register_officer.html')
        
        # Validate password (minimum 8 characters, includes letters and numbers)
        if len(password) < 8 or not any(char.isdigit() for char in password) or not any(char.isalpha() for char in password):
            flash("Password must be at least 8 characters long and include both letters and numbers.")
            conn.close()
            return render_template('register_officer.html')

        
        # Insert into Users table
        conn.execute('INSERT INTO Users (username, password, role, name, contact_info) VALUES (?, ?, ?, ?, ?)',
                     (username, password, 'officer', name, None))
        user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

        # Insert into Officer table
        conn.execute('INSERT INTO Officer (name, sector_no) VALUES (?, ?)',
                     (name, sector_no))

        conn.commit()
        conn.close()
        
        flash("Officer registered successfully.")
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

# Route to view water sources
@app.route('/manage_water_sources')
def manage_water_sources():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    water_sources = conn.execute('SELECT * FROM Reservoir').fetchall()
    conn.close()
    return render_template('manage_water_sources.html', water_sources=water_sources)

# Route to add a new water source
@app.route('/add_water_source', methods=['GET', 'POST'])
def add_water_source():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        water_level = request.form['water_level']
        capacity = request.form['capacity']
        location = request.form['location']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO Reservoir (name, water_level, capacity, location) VALUES (?, ?, ?, ?)',
            (name, water_level, capacity, location)
        )
        conn.commit()
        conn.close()

        flash('Water source added successfully!')
        return redirect(url_for('manage_water_sources'))

    return render_template('add_water_source.html')

# Route to update a water source
@app.route('/edit_water_source/<int:reservoir_id>', methods=['GET', 'POST'])
def edit_water_source(reservoir_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    water_source = conn.execute('SELECT * FROM Reservoir WHERE reservoir_id = ?', (reservoir_id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        water_level = request.form['water_level']
        capacity = request.form['capacity']
        location = request.form['location']

        conn.execute(
            'UPDATE Reservoir SET name = ?, water_level = ?, capacity = ?, location = ? WHERE reservoir_id = ?',
            (name, water_level, capacity, location, reservoir_id)
        )
        conn.commit()
        conn.close()

        flash('Water source updated successfully!')
        return redirect(url_for('manage_water_sources'))

    conn.close()
    return render_template('edit_water_source.html', water_source=water_source)

# Route to delete a water source
@app.route('/delete_water_source/<int:reservoir_id>', methods=['POST'])
def delete_water_source(reservoir_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM Reservoir WHERE reservoir_id = ?', (reservoir_id,))
    conn.commit()
    conn.close()

    flash('Water source deleted successfully!')
    return redirect(url_for('manage_water_sources'))

# Route to view water allocations
@app.route('/manage_water_allocations')
def manage_water_allocations():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    allocations = conn.execute('SELECT * FROM Water_Allocation').fetchall()
    conn.close()
    return render_template('manage_water_allocations.html', allocations=allocations)

# Route to add water allocation
@app.route('/add_water_allocation', methods=['GET', 'POST'])
def add_water_allocation():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        sector_no = request.form['sector_no']
        allocation_amount = request.form['allocation_amount']
        date = request.form['date']
        priority = request.form['priority']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO Water_Allocation (sector_no, allocation_amount, date, priority) VALUES (?, ?, ?, ?)',
            (sector_no, allocation_amount, date, priority)
        )
        conn.commit()
        conn.close()

        flash('Water allocation added successfully!')
        return redirect(url_for('manage_water_allocations'))

    return render_template('add_water_allocation.html')

@app.route('/view_reports')
def view_reports():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Calculate net water consumption (e.g., sum of all water allocations)
    total_consumption = conn.execute('SELECT SUM(allocation_amount) FROM Water_Allocation').fetchone()[0]

    # Calculate total water available in all reservoirs
    total_water_available = conn.execute('SELECT SUM(water_level) FROM Reservoir').fetchone()[0]

    # Calculate total reservoir capacity (for percentage full)
    total_capacity = conn.execute('SELECT SUM(capacity) FROM Reservoir').fetchone()[0]

    # Example data for incoming rate (e.g., could be stored in Reservoir or Water_Allocation)
    incoming_rate = conn.execute('SELECT AVG(allocation_amount) FROM Water_Allocation WHERE date > date("now", "-30 days")').fetchone()[0]

    conn.close()

    return render_template('view_reports.html', 
                           total_consumption=total_consumption, 
                           total_water_available=total_water_available, 
                           total_capacity=total_capacity,
                           incoming_rate=incoming_rate)

@app.route('/view_customers_in_sector')
def view_customers_in_sector():
    if 'user_id' not in session or session['role'] != 'officer':
        return redirect(url_for('login'))

    sector_no = session.get('sector_no')
    print(sector_no,"sect")
    conn = get_db_connection()

    # Retrieve customers in the officer's sector
    customers = conn.execute('''
        SELECT customer_id, name, sector_no
        FROM Customer
        WHERE sector_no = ?
    ''', (sector_no,)).fetchall()

    conn.close()
    return render_template('view_customers_in_sector.html', customers=customers)


@app.route('/fill_meter_reading/<int:customer_id>', methods=['GET', 'POST'])
def fill_meter_reading(customer_id):
    if 'user_id' not in session or session['role'] != 'officer':
        return redirect(url_for('login'))
    officer_id = session['user_id']
    conn = get_db_connection()

    # Check if customer belongs to the officer's sector
    customer = conn.execute('''
        SELECT * 
        FROM Customer 
        WHERE customer_id = ? 
    ''', (customer_id,)).fetchone()

    if not customer:
        flash("You do not have permission to access this customer.")
        conn.close()
        return redirect(url_for('view_customers_in_sector'))

    if request.method == 'POST':
        meter_reading = float(request.form['meter_reading'])
        reading_date = request.form['reading_date']

        # Insert meter reading
        try:
         # Insert meter reading
            conn.execute('''
        INSERT INTO MeterReadings (customer_id, reading_date, meter_reading)
        VALUES (?, ?, ?)
    ''', (customer_id, reading_date, meter_reading))
     
    # Calculate bill amount
            bill_amount = calculate_bill(meter_reading)
     
     # Insert new bill record
            conn.execute('''
         INSERT INTO Bills (customer_id, bill_date, amount_due, due_date)
         VALUES (?, ?, ?, DATE('now', '+30 days'))
     ''', (customer_id, reading_date, bill_amount))
     
            conn.commit()
            print("Meter reading and bill calculated successfully.")
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"An error occurred: {e}")
        finally:
            conn.close()


        flash("Meter reading and bill calculated successfully.")
        return redirect(url_for('view_customers_in_sector'))

    conn.close()
    return render_template('fill_meter_reading.html', customer=customer)

@app.route('/bills')
def bills():
    if 'user_id' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))
    
    customer_id = session.get('customer_id')  # Ensure customer_id is stored in session upon login
    bills = get_customer_bills(customer_id)
    
    return render_template('bills.html', bills=bills)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login')) 

if __name__ == '__main__':
    app.run(debug=True)
