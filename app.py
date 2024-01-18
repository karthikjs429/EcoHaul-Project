import os
import traceback
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas

import pyodbc
import requests
from flask import Flask, render_template, request, redirect, url_for, session, make_response
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Set up the SQL Server connection details
server = 'JS-KARTHIK\SQLEXPRESS'
database = 'eecohaul_project'
username = 'karthik'
password = 'Pass'
connection_string = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

# Establish the database connection
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

# Set up file upload configurations
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16 MB


def create_connection():
    return pyodbc.connect(connection_string)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return render_template('login.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        log_username = request.form['username']
        log_password = request.form['password']

        query = "SELECT id, user_type FROM Login WHERE username = ? AND password = ?"
        cursor.execute(query, (log_username, log_password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user.id
            session['user_type'] = user.user_type

            if user.user_type == 'driver':
                return redirect(url_for('driver_index'))
            elif user.user_type == 'supervisor':
                return redirect(url_for('supervisor_index'))
            else:
                return redirect(url_for('login'))  # Handle other user types

        else:
            return render_template('login.html', error='Invalid credentials')

    return render_template('login.html', error=None)


@app.route("/admin_index")
def admin_index():
    return render_template('admin_index.html')


def get_driver_id(driver_name):
    sql_query = "SELECT d_id FROM driver WHERE d_first_name = ? AND d_last_name = ?"
    try:
        cursor.execute(sql_query, driver_name)
        result = cursor.fetchone()
        if result:
            return result[0]
    except pyodbc.Error as e:
        print(f"Error fetching driver ID from the database: {e}")
        traceback.print_exc()
        raise  # Re-raise the exception after printing details


def fetch_drivers_from_database():
    try:
        with create_connection().cursor() as local_cursor:
            local_cursor.execute("SELECT d_id, d_first_name, d_last_name FROM driver")
            drivers = local_cursor.fetchall()
        return drivers
    except Exception as e:
        print(f"Error fetching drivers from the database: {e}")
        return []


def get_loader_id(loader_name):
    sql_query = "SELECT l_id FROM Loader WHERE l_first_name = ? AND l_last_name = ?"
    try:
        cursor.execute(sql_query, loader_name)
        result = cursor.fetchone()
        if result:
            return result[0]
    except pyodbc.Error as e:
        print(f"Error fetching loader ID from the database: {e}")
        traceback.print_exc()
        raise  # Re-raise the exception after printing details


def fetch_loaders_from_database():
    try:
        with create_connection().cursor() as local_cursor:
            local_cursor.execute("SELECT l_id, l_first_name, l_last_name FROM Loader")
            loaders = local_cursor.fetchall()
        return loaders
    except Exception as e:
        print(f"Error fetching loaders from the database: {e}")
        return []


@app.route("/driver_index")
def driver_index():
    if 'user_id' in session and 'user_type' in session and session['user_type'] == 'driver':
        # Add logic specific to the driver index page
        driver_id = session['user_id']

        query = "SELECT * FROM driver WHERE d_id = ?"
        cursor.execute(query, driver_id)
        driver_detail = cursor.fetchone()

        if driver_detail:
            return render_template('driver_index.html', driver_detail=driver_detail)

    return redirect(url_for('login'))


@app.route("/profile")
def profile():
    if 'user_id' in session and 'user_type' in session and session['user_type'] == 'driver':
        # Add logic specific to the driver index page
        driver_id = session['user_id']

        query = "SELECT * FROM driver WHERE d_id = ?"
        cursor.execute(query, driver_id)
        driver_detail = cursor.fetchone()

        if driver_detail:
            return render_template('profile.html', driver_detail=driver_detail)

    # If driver_detail is not available, pass an empty dictionary or handle it appropriately
    return render_template('profile.html', driver_detail={})


@app.route("/supervisor_profile")
def supervisor_profile():
    # Check if the user is logged in and is a supervisor
    if 'user_id' in session and 'user_type' in session and session['user_type'] == 'supervisor':
        # Get supervisor ID from the session
        supervisor_id = session['user_id']

        # Fetch supervisor details from the database
        query = "SELECT * FROM supervisors WHERE s_id = ?"
        cursor.execute(query, supervisor_id)
        supervisor_detail = cursor.fetchone()

        if supervisor_detail:
            # Render the HTML page and pass supervisor details to it
            return render_template('supervisor_profile.html', supervisor_detail=supervisor_detail)

    # Redirect to login if the user is not logged in or is not a supervisor
    return redirect(url_for('login'))


@app.route("/supervisor_index")
def supervisor_index():
    if 'user_id' in session and 'user_type' in session and session['user_type'] == 'supervisor':
        # Retrieve supervisor details from the session
        supervisor_id = session['user_id']

        # Query the database to get supervisor details based on supervisor_id
        query = "SELECT * FROM supervisors WHERE s_id = ?"
        cursor.execute(query, (supervisor_id,))
        supervisor_details = cursor.fetchone()

        if supervisor_details:
            # Pass the supervisor details to the template
            return render_template('supervisor_index.html', supervisor_details=supervisor_details)

    return redirect(url_for('login'))


@app.route("/admin_supervisor_reg", methods=['GET', 'POST'])
def admin_supervisor_reg():
    if request.method == 'POST':
        # Extract form data
        first_name = request.form['s_first_name']
        last_name = request.form['s_last_name']
        gender = request.form['s_gender']
        date_of_birth = request.form['s_date_of_birth']
        assign_to = request.form['s_assign_to']
        address1 = request.form['s_address1']
        state = request.form['s_state']
        address2 = request.form['s_address2']
        postcode = request.form['s_postcode']
        city = request.form['s_city']
        driver_license = request.form['s_driver_license']

        login_username = request.form['username']  # Use a different variable name
        login_password = request.form['password']  # Use a different variable name
        user_type = 'supervisor'

        try:
            # Insert data into the Login table
            login_query = "INSERT INTO Login (username, password, user_type) VALUES (?, ?, ?)"
            cursor.execute(login_query, (login_username, login_password, user_type))
            conn.commit()

            # Get the last identity value generated during the session
            cursor.execute("SELECT @@IDENTITY AS login_id")
            login_id = cursor.fetchone().login_id

            # Insert data into the supervisors table
            query = """
                INSERT INTO supervisors (
                    s_first_name, s_last_name, s_gender, s_date_of_birth,
                    s_assign_to, s_address1, s_state, s_address2, s_postcode, s_city, s_driver_license, login_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (
                first_name, last_name, gender, date_of_birth, assign_to, address1, state, address2, postcode, city,
                driver_license, login_id
            ))
            conn.commit()

            return redirect(url_for('admin_supervisor_reg'))

        except pyodbc.Error as e:
            conn.rollback()
            return f"Error: {str(e)}"

    # If it's a GET request, render the form
    return render_template('admin_supervisor_reg.html')


@app.route("/admin_loader_reg", methods=['GET', 'POST'])
def admin_loader_reg():
    if request.method == 'POST':
        # Extract form data
        first_name = request.form['l_first_name']
        last_name = request.form['l_last_name']
        email = request.form['l_email']
        gender = request.form['l_gender']
        date_of_birth = request.form['l_date_of_birth']
        address = request.form['l_address']
        state = request.form['l_state']
        postcode = request.form['l_postcode']
        city = request.form['l_city']

        # Insert data into the loaders table
        query = """
            INSERT INTO Loader (
                l_first_name, l_last_name, l_email, l_gender, l_date_of_birth,
                l_address, l_state, l_postcode, l_city
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (
            first_name, last_name, email, gender, date_of_birth, address, state, postcode, city
        ))
        conn.commit()

        return redirect(url_for('admin_index'))

    # If it's a GET request, render the form
    return render_template('admin_loader_reg.html')


@app.route("/display_loader")
def display_loader():
    # Execute the SQL query to fetch all supervisor details
    cursor.execute("""
        SELECT * FROM Loader;
    """)

    # Fetch all the supervisor details
    loaders_data = cursor.fetchall()

    return render_template('display_loader.html', loaders_data=loaders_data)


@app.route("/display_loader/delete_loader/<int:id>", methods=['GET', 'POST'])
def delete_loader(id):
    if request.method == 'POST':
        # Assuming you have a loaders table in your database
        cursor.execute("DELETE FROM Loader WHERE l_id = ?", (id,))
        conn.commit()

        return redirect(url_for('display_loader'))
    else:
        # Fetch loader details for confirmation message
        cursor.execute("SELECT * FROM Loader WHERE l_id = ?", (id,))
        loader = cursor.fetchone()

        return render_template('delete_loader.html', loader_id=id, loader=loader)


@app.route("/display_loader/edit_loader/<int:id>", methods=['GET', 'POST'])
def edit_loader(id):
    if request.method == 'POST':
        # Assuming you have a loaders table in your database
        new_first_name = request.form.get('l_first_name')
        new_last_name = request.form.get('l_last_name')
        new_email = request.form.get('l_email')
        new_gender = request.form.get('l_gender')
        new_date_of_birth = request.form.get('l_date_of_birth')
        new_address = request.form.get('l_address')
        new_state = request.form.get('l_state')
        new_postcode = request.form.get('l_postcode')
        new_city = request.form.get('l_city')
        # Add other form fields for editing

        cursor.execute("""
            UPDATE Loader 
            SET l_first_name=?, l_last_name=?, l_email=?, l_gender=?, l_date_of_birth=?, 
                l_address=?, l_state=?, l_postcode=?, l_city=?
            WHERE l_id=?
        """, (new_first_name, new_last_name, new_email, new_gender, new_date_of_birth,
              new_address, new_state, new_postcode, new_city, id))
        conn.commit()

        return redirect(url_for('display_loader'))
    else:
        # Fetch loader details for pre-populating the form
        cursor.execute("SELECT * FROM Loader WHERE l_id = ?", (id,))
        loader = cursor.fetchone()

        return render_template('edit_loader.html', loader_id=id, loader=loader)


@app.route("/display_supervisors", methods=['GET', 'POST'])
def display_supervisors():
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        # Execute the SQL query to fetch supervisor details within the date range
        cursor.execute("""
            SELECT * FROM supervisors
            WHERE registration_date BETWEEN ? AND ?;
        """, (start_date, end_date))
    else:
        # If it's a GET request, fetch all supervisor details without filtering
        cursor.execute("""
            SELECT * FROM supervisors;
        """)

    # Fetch all the supervisor details
    supervisors_data = cursor.fetchall()

    return render_template('display_supervisors.html', supervisors_data=supervisors_data)


@app.route("/display_supervisors/delete_supervisor/<int:id>", methods=['GET', 'POST'])
def delete_supervisor(id):
    if request.method == 'POST':
        # Assuming you have a supervisors table in your database
        cursor.execute("DELETE FROM supervisors WHERE s_id = ?", (id,))
        conn.commit()

        return redirect(url_for('display_supervisors'))
    else:
        # Fetch supervisor details for confirmation message
        cursor.execute("SELECT * FROM supervisors WHERE s_id = ?", (id,))
        supervisor = cursor.fetchone()

        return render_template('delete_supervisor.html', supervisor_id=id, supervisor=supervisor)


@app.route("/display_supervisors/edit_supervisor/<int:id>", methods=['GET', 'POST'])
def edit_supervisor(id):
    if request.method == 'POST':
        # Assuming you have a supervisors table in your database
        new_first_name = request.form.get('s_first_name')
        new_last_name = request.form.get('s_last_name')
        new_gender = request.form.get('s_gender')
        new_date_of_birth = request.form.get('s_date_of_birth')
        new_assign_to = request.form.get('s_assign_to')
        new_address1 = request.form.get('s_address1')
        new_state = request.form.get('s_state')
        new_address2 = request.form.get('s_address2')
        new_postcode = request.form.get('s_postcode')
        new_city = request.form.get('s_city')
        new_driver_license = request.form.get('s_driver_license')
        # Add other form fields for editing

        cursor.execute("""
            UPDATE supervisors 
            SET s_first_name=?, s_last_name=?, s_gender=?, s_date_of_birth=?, 
                s_assign_to=?, s_address1=?, s_state=?, s_address2=?, 
                s_postcode=?, s_city=?, s_driver_license=?
            WHERE s_id=?
        """, (new_first_name, new_last_name, new_gender, new_date_of_birth,
              new_assign_to, new_address1, new_state, new_address2,
              new_postcode, new_city, new_driver_license, id))
        conn.commit()

        return redirect(url_for('display_supervisors'))
    else:
        # Fetch supervisor details for pre-populating the form
        cursor.execute("SELECT * FROM supervisors WHERE s_id = ?", (id,))
        supervisor = cursor.fetchone()

        return render_template('edit_supervisor.html', supervisor_id=id, supervisor=supervisor)


@app.route("/admin_driver_reg", methods=['GET', 'POST'])
def admin_driver_reg():
    if request.method == 'POST':
        first_name = request.form['d_first_name']
        last_name = request.form['d_last_name']
        gender = request.form['d_gender']
        date_of_birth = request.form['d_date_of_birth']
        assign_to = request.form['d_assign_to']
        address1 = request.form['d_address1']
        state = request.form['d_state']
        address2 = request.form['d_address2']
        postcode = request.form['d_postcode']
        city = request.form['d_city']
        driver_license = request.form['d_driver_license']

        login_username = request.form['username']  # Use a different variable name
        login_password = request.form['password']  # Use a different variable name
        user_type = 'driver'

        try:
            # Insert data into the Login table
            login_query = "INSERT INTO Login (username, password, user_type) VALUES (?, ?, ?)"
            cursor.execute(login_query, (login_username, login_password, user_type))
            conn.commit()

            # Get the last identity value generated during the session
            cursor.execute("SELECT @@IDENTITY AS login_id")
            login_id = cursor.fetchone().login_id

            # Insert data into the Driver table
            driver_query = """
                        INSERT INTO driver (d_first_name, d_last_name, d_gender, d_date_of_birth, d_assign_to, 
                                            d_address1, d_state, d_address2, d_postcode, d_city, d_driver_license, login_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
            cursor.execute(driver_query, (
                first_name, last_name, gender, date_of_birth, assign_to, address1, state, address2, postcode, city,
                driver_license, login_id))
            conn.commit()

            return redirect(url_for('admin_index'))

        except pyodbc.Error as e:
            conn.rollback()
            return f"Error: {str(e)}"

    return render_template('admin_driver_reg.html')


@app.route("/display_driver")
def display_driver():
    # Execute the SQL query to fetch all driver details
    cursor.execute("""
        SELECT * FROM driver;
    """)

    # Fetch all the driver details
    drivers_data = cursor.fetchall()

    return render_template('display_driver.html', drivers_data=drivers_data)


@app.route("/display_driver/delete_driver/<int:id>", methods=['GET', 'POST'])
def delete_driver(id):
    if request.method == 'POST':
        # Assuming you have a driver table in your database
        cursor.execute("DELETE FROM driver WHERE d_id = ?", (id,))
        conn.commit()

        return redirect(url_for('display_driver'))
    else:
        # Fetch driver details for confirmation message
        cursor.execute("SELECT * FROM driver WHERE d_id = ?", (id,))
        driver = cursor.fetchone()

        return render_template('delete_driver.html', driver_id=id, driver=driver)


@app.route("/display_driver/edit_driver/<int:id>", methods=['GET', 'POST'])
def edit_driver(id):
    if request.method == 'POST':
        # Assuming you have a driver table in your database
        new_first_name = request.form.get('d_first_name')
        new_last_name = request.form.get('d_last_name')
        new_gender = request.form.get('d_gender')
        new_date_of_birth = request.form.get('d_date_of_birth')
        new_assign_to = request.form.get('d_assign_to')
        new_address1 = request.form.get('d_address1')
        new_state = request.form.get('d_state')
        new_address2 = request.form.get('d_address2')
        new_postcode = request.form.get('d_postcode')
        new_city = request.form.get('d_city')
        new_driver_license = request.form.get('d_driver_license')
        # Add other form fields for editing

        cursor.execute("""
            UPDATE driver 
            SET d_first_name=?, d_last_name=?, d_gender=?, d_date_of_birth=?, 
                d_assign_to=?, d_address1=?, d_state=?, d_address2=?, 
                d_postcode=?, d_city=?, d_driver_license=?
            WHERE d_id=?
        """, (new_first_name, new_last_name, new_gender, new_date_of_birth,
              new_assign_to, new_address1, new_state, new_address2,
              new_postcode, new_city, new_driver_license, id))
        conn.commit()

        return redirect(url_for('display_driver'))
    else:
        # Fetch driver details for pre-populating the form
        cursor.execute("SELECT * FROM driver WHERE d_id = ?", (id,))
        driver = cursor.fetchone()

        return render_template('edit_driver.html', driver_id=id, driver=driver)


@app.route("/add_products", methods=['GET', 'POST'])
def add_products():
    if request.method == 'POST':
        # Extract form data
        p_name = request.form['p_name']
        p_type = request.form['p_type']
        p_price = request.form['p_price']
        p_size_liters = request.form['p_size_liters']

        # Handle file upload
        if 'p_image' in request.files:
            file = request.files['p_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                p_image = filename
            else:
                p_image = None
        else:
            p_image = None

        # Insert data into the products table
        query = """
            INSERT INTO products_table (p_name, p_type, p_image, p_price, p_size_liters) VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(query, (p_name, p_type, p_image, p_price, p_size_liters))
        conn.commit()

        return redirect(url_for('display_products'))

    # If it's a GET request, render the form
    return render_template('add_products.html')


@app.route("/display_products")
def display_products():
    # Assuming you have a 'products' table with appropriate columns
    query = "SELECT * FROM products_table"
    cursor.execute(query)
    products_data = cursor.fetchall()
    return render_template('display_products.html', products_data=products_data)


@app.route("/delete_product/<int:id>", methods=['GET'])
def delete_product(id):
    # Assuming you have a 'products_table' table with an 'id' column
    query = "DELETE FROM products_table WHERE p_id = ?"
    cursor.execute(query, (id,))
    conn.commit()
    return redirect(url_for('display_products'))


@app.route('/admin_map_reg', methods=['GET', 'POST'])
def admin_map_reg():
    if request.method == 'POST':
        # Get form data
        map_zone = request.form.get('map_zone')

        # Handle file upload
        map_picture = request.files['map_picture']
        if map_picture and allowed_file(map_picture.filename):
            # Save the file to a folder
            map_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(map_picture.filename))
            map_picture.save(map_picture_path)

            # Insert data into the MS SQL Server database
            try:
                with create_connection().cursor() as cursor:
                    cursor.execute("INSERT INTO Map (map_zone, map_picture) VALUES (?, ?)", map_zone, map_picture_path)
                    create_connection().commit()
            except Exception as e:
                # Handle the exception (log, display error message, etc.)
                print(f"Error inserting data into the database: {e}")

            # Redirect to the admin index or wherever appropriate
            return redirect(url_for('admin_index'))

    # Render the form template
    return render_template('admin_map_reg.html')


@app.route("/admin_add_products")
def admin_add_products():
    return render_template('admin_add_products.html')


def get_help_requests():
    query = "SELECT [h_id], [h_message], [h_date], [login_id] FROM helprequest"
    cursor.execute(query)
    return cursor.fetchall()


@app.route("/supervisor_message", methods=['POST', 'GET'])
def supervisor_message():
    if request.method == 'POST':
        # Get the driver ID from the session
        supervisor_id = session.get('user_id')

        # Check if driver_id is None or not
        if supervisor_id is None:
            return "Supervisor ID not found in the session. Please log in."

        su_message = request.form['gm_message']
        su_date = datetime.now().strftime("%Y-%m-%d")

        # Insert the global message into the database
        query_insert_global_message = "INSERT INTO supervisormessage (su_message, su_date, login_id) VALUES (?, ?, ?)"
        cursor.execute(query_insert_global_message, (su_message, su_date, supervisor_id))
        conn.commit()

        # Redirect to avoid form resubmission issues
        return redirect(url_for('supervisor_message'))

    return render_template('supervisor_message.html')


@app.route("/driver_message", methods=['POST', 'GET'])
def driver_message():
    if request.method == 'POST':
        # Get the driver ID from the session
        driver_id = session.get('user_id')

        # Check if driver_id is None or not
        if driver_id is None:
            return "Driver ID not found in the session. Please log in."

        gm_message = request.form['gm_message']
        gm_date = datetime.now().strftime("%Y-%m-%d")

        # Insert the global message into the database
        query_insert_global_message = "INSERT INTO globalmessage (gm_message, gm_date, login_id) VALUES (?, ?, ?)"
        cursor.execute(query_insert_global_message, (gm_message, gm_date, driver_id))
        conn.commit()

        # Redirect to avoid form resubmission issues
        return redirect(url_for('driver_message'))

    # Fetch help requests from the database
    query_help_requests = "SELECT h_id, h_message, h_date, login_id FROM helprequest"
    cursor.execute(query_help_requests)
    help_requests_data = cursor.fetchall()

    # Render the HTML page and pass data to it
    return render_template('driver_message.html', help_requests_data=help_requests_data)


@app.route("/request_help", methods=['POST', 'GET'])
def request_help():
    if request.method == 'POST':
        # Get the driver ID from the session
        driver_id = session.get('user_id')

        if driver_id is None:
            return "Driver ID not found in the session. Please log in."

        h_message = request.form['h_message']
        h_date = request.form['h_date']

        try:
            # Insert the help request into the database, including the driver ID
            query = "INSERT INTO helprequest (h_message, h_date, login_id) VALUES (?, ?, ?)"
            cursor.execute(query, (h_message, datetime.strptime(h_date, "%Y-%m-%d"), driver_id))
            conn.commit()

            return redirect(url_for('driver_index'))

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return render_template('error.html', message='An error occurred while processing your request.')

    return render_template('request_help.html')


@app.route('/report_customer', methods=['POST', 'GET'])
def report_customer():
    if request.method == 'POST':
        # Retrieve user_id from the session
        user_id = session.get('user_id')

        if user_id is None:
            return "User ID not found in the session. Please log in."

        house_no = request.form.get('co_house_no')
        street = request.form.get('co_street')
        city = request.form.get('co_city')
        action = request.form.get('co_action')
        date = request.form.get('co_date')
        desc = request.form.get('co_desc')

        # Define cursor and conn outside the try block
        cursor = None
        conn = None

        try:
            with create_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "INSERT INTO CivilianComplaintReports (co_house_no, co_street, co_city, co_action, co_date, co_desc, login_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (house_no, street, city, action, date, desc, user_id))

                conn.commit()

                # Handle file upload
                if 'img' in request.files:
                    file = request.files['img']
                    if file.filename != '' and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        # If you want to store the file path in the database, you can do it here

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            return render_template('error.html', message='An error occurred while processing your request.')

        finally:
            # Close the cursor and connection in the finally block
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return redirect(url_for('driver_index'))

    return render_template('report_customer.html')


@app.route('/leave_request', methods=['GET', 'POST'])
def leave_request():
    if request.method == 'POST':
        leave_message = request.form.get('leave_message')
        leave_start_date = request.form.get('leave_start_date')
        leave_end_date = request.form.get('leave_end_date')

        # Retrieve user_id from the session (assuming you have set it during login)
        user_id = session.get('user_id')

        if user_id is None:
            return "User ID not found in the session. Please log in."

        try:
            with create_connection() as conn:
                cursor = conn.cursor()

                # Insert leave request into the database
                cursor.execute(
                    "INSERT INTO LeaveRequests (leave_message, leave_start_date, leave_end_date, user_id) VALUES (?, ?, ?, ?)",
                    (leave_message, leave_start_date, leave_end_date, user_id)
                )

                conn.commit()

        except pyodbc.Error as e:
            print(f"Database error: {e}")
            traceback.print_exc()  # Print detailed error information

    return render_template('leave_request.html')


@app.route('/leave_requests')
def leave_requests():
    try:
        with create_connection() as conn:
            cursor = conn.cursor()

            # Join the LeaveRequests table with the driver table using the user_id
            query = """
                SELECT lr.leave_id, lr.leave_message, lr.leave_start_date, lr.leave_end_date, 
                       lr.submitted_at, lr.status, d.d_first_name, d.d_last_name
                FROM LeaveRequests lr
                JOIN driver d ON lr.user_id = d.d_id
            """
            cursor.execute(query)
            leave_requests_data = cursor.fetchall()

    except pyodbc.Error as e:
        print(f"Database error: {e}")

    return render_template('leave_requests.html', leave_requests_data=leave_requests_data)


@app.route('/approve_leave/<int:leave_id>')
def approve_leave(leave_id):
    try:
        with create_connection() as conn:
            cursor = conn.cursor()

            # Update the status to 'Approved' in the LeaveRequests table
            query = "UPDATE LeaveRequests SET status = 'Approved' WHERE leave_id = ?"
            cursor.execute(query, leave_id)
            conn.commit()

    except pyodbc.Error as e:
        print(f"Database error: {e}")

    return redirect(url_for('leave_requests'))


@app.route('/delete_leave/<int:leave_id>')
def delete_leave(leave_id):
    try:
        with create_connection() as conn:
            cursor = conn.cursor()

            # Update the status to 'Deleted' in the LeaveRequests table
            query = "UPDATE LeaveRequests SET status = 'Deleted' WHERE leave_id = ?"
            cursor.execute(query, leave_id)
            conn.commit()

    except pyodbc.Error as e:
        print(f"Database error: {e}")

    return redirect(url_for('leave_requests'))


@app.route('/leave_status')
def leave_status():
    try:
        with create_connection() as conn:
            cursor = conn.cursor()

            # Join the LeaveRequests table with the driver table using the user_id
            query = """
                SELECT lr.leave_id, lr.leave_message, lr.leave_start_date, lr.leave_end_date, 
                       lr.submitted_at, lr.status, d.d_first_name, d.d_last_name
                FROM LeaveRequests lr
                JOIN driver d ON lr.user_id = d.d_id
            """
            cursor.execute(query)
            leave_requests_data = cursor.fetchall()

    except pyodbc.Error as e:
        print(f"Database error: {e}")

    return render_template('leave_status.html', leave_requests_data=leave_requests_data)


def fetch_maps_from_database():
    try:
        with create_connection().cursor() as local_cursor:
            local_cursor.execute("SELECT map_id, map_zone FROM Map")
            maps = local_cursor.fetchall()
        return maps
    except Exception as e:
        print(f"Error fetching maps from the database: {e}")
        return []


def get_map_id(map_id):
    try:
        sql_query = "SELECT map_id FROM Map WHERE map_zone = ?"
        cursor.execute(sql_query, (map_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        else:
            raise ValueError(f"No result found for map_id: {map_id}")
    except pyodbc.Error as e:
        print(f"Database error in get_map_id: {e}")
        traceback.print_exc()
        raise  # Re-raise the exception after printing details


# ... (other functions and configurations)


@app.route('/error_page')
def error_page():
    error_message = request.args.get('error_message', 'An error occurred.')
    return render_template('error_page.html', error_message=error_message)


@app.route('/supervisor_assign_map', methods=['POST', 'GET'])
def supervisor_assign_map():
    if request.method == 'POST':
        try:
            map_id = request.form.get('map_id')
            driver_id = request.form.get('d_assign_to_driver')
            loader_id = request.form.get('d_assign_to_loader')
            assign_map_note = request.form.get('assign_map_note')
            print(map_id,driver_id,loader_id,assign_map_note)
            # Insert data into the Assignment_map table
            with conn.cursor() as local_cursor:
                print("in the local cursor")
                # local_cursor.execute( "Select * from Assignment_maps")
                # print(cursor.fetchall())
                local_cursor.execute(
                    "INSERT INTO Assignment_maps (map_id, driver_id, loader_id, assign_map_note) VALUES (?, ?, ?, ?)",
                    (map_id, driver_id, loader_id, assign_map_note))
                conn.commit()

        except pyodbc.Error as e:
            # Handle the database exception
            error_message = f"Database error in supervisor_assign_map: {e}"
            print(error_message)
            # Redirect to the error page with the custom error message
            return render_template('error_page.html', error_message=error_message)

    # For GET requests, render the template for the supervisor_assign_map page
    maps = fetch_maps_from_database()
    drivers = fetch_drivers_from_database()
    loaders = fetch_loaders_from_database()
    return render_template('supervisor_assign_map.html', maps=maps, loaders=loaders, drivers=drivers)


# Your Google Maps API key
API_KEY = 'AIzaSyCzeUI8UiKLKL-QaZ7Yp9XW5NnIhHqGMr4'


def get_coordinates(address):
    base_url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'address': address, 'key': API_KEY}

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        if 'results' in data and data['results']:
            result = data['results'][0]
            geometry = result.get('geometry', {})
            location = geometry.get('location', {})
            latitude = location.get('lat')
            longitude = location.get('lng')

            if latitude is not None and longitude is not None:
                return latitude, longitude

    except requests.exceptions.RequestException as e:
        print(f"Error fetching coordinates: {e}")

    print(f"API response content: {response.content}")
    return None


@app.route('/redirect_to_map', methods=['GET'])
def redirect_to_map():
    address = request.args.get('address', '').strip()

    if not address:
        return "Invalid address. Please provide a valid address."

    coordinates = get_coordinates(address)

    if coordinates:
        map_url = f'https://www.google.com/maps/@{coordinates[0]},{coordinates[1]},18z'
        return redirect(map_url, code=302)
    else:
        return f"Unable to get coordinates for address: {address}."


@app.route('/get_current_location', methods=['GET'])
def get_current_location():
    return render_template('get_current_location.html')


def get_help_requests_data():
    try:
        # Fetch help request data with driver names from the database
        query = """
            SELECT hr.*, d.d_first_name, d.d_last_name
            FROM helprequest hr
            JOIN driver d ON hr.login_id = d.login_id
        """
        cursor.execute(query)
        help_requests_data = cursor.fetchall()
        return help_requests_data
    except pyodbc.Error as e:
        # Log the error or handle it as needed
        print(f"Error fetching help requests: {e}")
        return []


@app.route('/view_assignment_details', methods=['GET'])
def view_assignment_details():
    try:
        with create_connection() as conn:
            cursor = conn.cursor()

            # Fetch assignment details by joining Map, Loader, Driver, and Assignment_map tables
            query = """
                SELECT
                    am.assignment_id,
                    m.map_zone,
                    l.l_first_name AS loader_first_name,
                    l.l_last_name AS loader_last_name,
                    d.d_first_name AS driver_first_name,
                    d.d_last_name AS driver_last_name,
                    am.assign_map_note,
                    am.assignment_date
                FROM
                    Assignment_maps am
                INNER JOIN
                    Map m ON am.map_id = m.map_id
                INNER JOIN
                    Loader l ON am.loader_id = l.l_id
                INNER JOIN
                    driver d ON am.driver_id = d.d_id;
            """

            cursor.execute(query)
            assignment_details = cursor.fetchall()

    except pyodbc.Error as e:
        print(f"Database error: {e}")
        return "An error occurred while processing your request."

    return render_template('view_assignment_details.html', assignment_details=assignment_details)


employee_data = {
    'supervisor': {'hourly_rate': 20},
    'driver': {'hourly_rate': 18},
    'loader': {'hourly_rate': 16.65}
}


@app.route('/payroll_calculator', methods=['GET', 'POST'])
def payroll_calculator():
    if request.method == 'POST':
        hours_worked = float(request.form['hours_worked'])
        user_role = request.form['user_role']

        employee_info = employee_data.get(user_role, {})
        hourly_rate = employee_info.get('hourly_rate', 0)

        tax_deducted = 0.13 * (hours_worked * hourly_rate)  # Assuming 13% tax
        gross_total_salary = hours_worked * hourly_rate - tax_deducted

        # Store data in the MS SQL Server database
        try:
            with conn.cursor() as cursor:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO PayrollData (user_role, hours_worked, hourly_rate, tax_deducted, gross_total_salary)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_role, hours_worked, hourly_rate, tax_deducted, gross_total_salary))
                conn.commit()
        except pyodbc.Error as e:
            print(f"Database error: {e}")

        return render_template('payroll_result.html',
                               employee_role=user_role,
                               hours_worked=hours_worked,
                               tax_deducted=tax_deducted,
                               gross_total_salary=gross_total_salary)

    return render_template('payroll_calculator.html')


# Add a route to display the payroll data as a PDF
@app.route('/payroll_pdf')
def payroll_pdf():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM PayrollData")
            payroll_data = cursor.fetchall()
    except pyodbc.Error as e:
        print(f"Database error: {e}")
        payroll_data = []

    buffer = BytesIO()

    # Create a PDF document
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Payroll Data")

    y_position = 780
    for row in payroll_data:
        y_position -= 20
        p.drawString(100, y_position, f"ID: {row[0]}, Role: {row[1]}, Hours Worked: {row[2]}, Tax Deducted: {row[4]}, Gross Total Salary: {row[5]}")

    p.showPage()
    p.save()

    buffer.seek(0)

    response = make_response(buffer.read())
    response.mimetype = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=payroll_data.pdf'
    return response


@app.route('/view_complaints', methods=['GET'])
def view_complaints():
    with conn.cursor() as cursor:
        select_query = "SELECT c_desc FROM complaints"
        cursor.execute(select_query)
        complaints = cursor.fetchall()

    return render_template('view_complaints.html', complaints=complaints)


@app.route('/customer_feedback', methods=['GET'])
def view_feedback():
    return render_template('customer_feedback.html')


@app.route('/customer_feedback', methods=['POST'])
def customer_feedback():
    customer_name = request.form['customerName']
    email = request.form['email']
    phone = request.form['phone']
    feedback_type = request.form['feedbackType']
    feedback_text = request.form['feedback']

    # Here, you can process the feedback data, store it in a database, send emails, etc.
    # For simplicity, let's just print the information to the console.
    print(f"Customer Name: {customer_name}")
    print(f"Email: {email}")
    print(f"Phone: {phone}")
    print(f"Feedback Type: {feedback_type}")
    print(f"Feedback: {feedback_text}")

    success_message = "Feedback submitted successfully!"
    return render_template('admin_index.html', message=success_message)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
