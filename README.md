# Water Supply Management

A simple Flask-based web application for managing water supply records with user authentication.  
It uses **SQLite** as the database and **Werkzeug** for password hashing.

---

## Features
- User registration and login system
- Secure password storage (hashed with Werkzeug)
- Session-based authentication
- SQLite database integration
- Flash messages for user feedback

---

## Requirements
- Python 3.8+
- Flask
- Werkzeug

Install dependencies with:

```bash
pip install -r requirements.txt
```


## Setup & Usage

1. **Clone the repository**

   ```bash
   git clone https://github.com/hermanumrao/water_suply_management.git
   cd water_suply_management
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Linux / Mac
   venv\Scripts\activate      # On Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**

   ```bash
   python app.py
   ```

5. **Access the app**
   Open your browser and visit: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Project Structure

```
water_suply_management/
│── app.py              # Main Flask application
│── requirements.txt    # Project dependencies
│── templates/          # HTML templates
│── static/             # CSS, JS, images
└── README.md           # Project documentation
```

---

## Notes

* Replace `app.secret_key` in `app.py` with a strong, unique secret key before deploying.
* SQLite is included by default with Python, so no extra installation is required.

---

## License

This project is licensed under the MIT License.
