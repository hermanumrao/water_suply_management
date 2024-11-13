-- Table for storing user login details
CREATE TABLE Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'officer', 'customer')),
    name TEXT,
    contact_info TEXT
);

-- Table for customer information
CREATE TABLE Customer (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    userid INTEGER,
    name TEXT NOT NULL,
    sector_no INTEGER,
    reservoir_id INTEGER,
    connections INTEGER,
    FOREIGN KEY (userid) REFERENCES Users(user_id),
    FOREIGN KEY (reservoir_id) REFERENCES Reservoir(reservoir_id)
);

-- Table for locality information
CREATE TABLE Locality (
    sector_no INTEGER PRIMARY KEY,
    area_name TEXT NOT NULL,
    water_supply_date DATE,
    officer_id INTEGER,
    reservoir_id INTEGER,
    FOREIGN KEY (officer_id) REFERENCES Officer(officer_id),
    FOREIGN KEY (reservoir_id) REFERENCES Reservoir(reservoir_id)
);

-- Table for billing information
CREATE TABLE Bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    bill_date TEXT,
    amount_due REAL,
    due_date TEXT,
    FOREIGN KEY (customer_id) REFERENCES Users(user_id)
);

-- Table for storing meter readings
CREATE TABLE MeterReadings (
    reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    reading_date TEXT,
    meter_reading REAL,
    FOREIGN KEY (customer_id) REFERENCES Customer(customer_id)
);


-- Table for officer information
CREATE TABLE Officer (
    officer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sector_no INTEGER,
    FOREIGN KEY (sector_no) REFERENCES Locality(sector_no)
);

-- Table for reservoir (water source) details
CREATE TABLE Reservoir (
    reservoir_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    water_level REAL,
    capacity REAL,
    status TEXT,
    location TEXT
);

-- Table for managing water allocation to different sectors
CREATE TABLE Water_Allocation (
    allocation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_no INTEGER,
    allocation_amount REAL,
    date DATE,
    priority TEXT CHECK(priority IN ('agriculture', 'industry', 'residential')),
    FOREIGN KEY (sector_no) REFERENCES Locality(sector_no)
);

-- Table for storing report data for analytics
CREATE TABLE Reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT CHECK(type IN ('usage', 'availability', 'allocation')),
    data TEXT,
    date DATE
);

-- Example indices for performance improvement on common queries
CREATE INDEX idx_customer_sector ON Customer(sector_no);
CREATE INDEX idx_locality_sector ON Locality(sector_no);
CREATE INDEX idx_bills_customer ON Bills(customer_id);
CREATE INDEX idx_reports_date ON Reports(date);

-- Trigger to delete bills older than one year whenever a new bill is inserted
CREATE TRIGGER delete_old_bills
AFTER INSERT ON Bills
BEGIN
    DELETE FROM Bills
    WHERE bill_date < DATE('now', '-1 year');
END;

-- Trigger to delete meter readings older than one year whenever a new reading is inserted
CREATE TRIGGER delete_old_meter_readings
AFTER INSERT ON MeterReadings
BEGIN
    DELETE FROM MeterReadings
    WHERE reading_date < DATE('now', '-1 year');
END;


-- Optional: Insert default admin user
INSERT INTO Users (username, password, role, name, contact_info) 
VALUES ('admin', 'password', 'admin', 'Administrator', 'admin@example.com');
