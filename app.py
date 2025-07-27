from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash
import mysql.connector
import os
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from datetime import datetime
import locale

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_fallback_secret_key')
app.config['UPLOAD_FOLDER'] = "uploads"
ALLOWED_EXTENSIONS = {'csv'}

# MySQL connection
def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# File extension check
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Currency Filter
@app.template_filter('currency')
def currency_format(value):
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        return locale.currency(value, grouping=True)
    except:
        return value

@app.route('/')
def index():
    return render_template('index.html')

def get_db():
    return mysql.connector.connect(
        host="DB_HOST",
        user="DB_USER",
        password="DB_PASS",
        database="DB_NAME"
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s AND role=%s", (email, password, role))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['role'] = role
            return redirect('/admin' if role == 'admin' else '/dashboard')
        else:
            flash('Invalid email and password', 'error')  # Correct category for template filter

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            error = "Passwords do not match."
        else:
            try:
                db = mysql.connector.connect(
                    host='DB_HOST',
                    user='DB_USER',
                    password='DB_PASS',
                    database='DB_NAME'
                )
                cursor = db.cursor(dictionary=True)

                # Check if email already exists
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                existing_user = cursor.fetchone()

                if existing_user:
                    error = "Email already exists."
                else:
                    # Insert new user
                    cursor.execute("""
                        INSERT INTO users (name, email, password, role)
                        VALUES (%s, %s, %s, %s)
                    """, (name, email, password, 'user'))
                    db.commit()
                    return redirect('/login')

            except mysql.connector.Error as err:
                error = f"Database error: {err}"

            finally:
                cursor.close()
                db.close()

    return render_template('signup.html', error=error)



@app.route('/select_month_year', methods=['GET', 'POST'])
def select_month_year():
    if request.method == 'POST':
        # Fetch values from form
        month = request.form.get('month')
        year = request.form.get('year')
        transaction_type = request.form.get('transaction_type')

        # Validation
        if not month or not year or not transaction_type:
            flash("Please select all fields.")
            return redirect('/select_month_year')

        # Save in session
        session['selected_month'] = month
        session['selected_year'] = int(year)

        # Normalize transaction_type to match your existing route
        if transaction_type not in ['Income', 'Expense']:
            flash("Invalid transaction type selected.")
            return redirect('/select_month_year')

        # Redirect to transaction input form
        return redirect(f"/add_transaction/{transaction_type.lower()}")

    return render_template("select_month_year.html")

@app.route('/add_transaction/<trans_type>', methods=['GET', 'POST'])
def add_transaction(trans_type):
    if trans_type not in ['income', 'expense']:
        flash("Invalid transaction type.")
        return redirect('/select_month_year')

    month = session.get('selected_month')
    year = session.get('selected_year')

    if not month or not year:
        flash("Please select a month and year first.")
        return redirect('/select_month_year')

    categories = ['Food','Health','Shopping','Rent','Education','Entertainment','Transport', 'Utilities', 'Others']

    if request.method == 'POST':
        amount = request.form['amount']
        user_id = session['user_id']
        category = request.form.get('category') if trans_type == 'expense' else None
        description = request.form.get('description') if trans_type == 'expense' else None

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transactions (user_id, transaction_type, category, description, amount, month, year)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            trans_type.capitalize(),
            category,
            description,
            amount,
            month,
            year
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash(f"{trans_type.capitalize()} added successfully!")
        return redirect('/dashboard')

    return render_template("add_transaction.html", trans_type=trans_type, month=month, year=year, categories=categories)


@app.route('/summary')
def summary():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT month, year, category, description, amount, transaction_type, date, time
        FROM transactions
        WHERE user_id = %s
        ORDER BY year DESC, month DESC, date DESC
    """, (user_id,))
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('summary.html', transactions=transactions)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect('/login')

    month = session.get('selected_month')
    year = session.get('selected_year')

    if not month or not year:
        flash("Please select a month and year first.")
        return redirect('/select_month_year')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT SUM(amount) AS total_income
        FROM transactions
        WHERE user_id=%s AND year=%s AND transaction_type='Income' AND month=%s
    """, (session['user_id'], year, month))
    total_income = cursor.fetchone()['total_income'] or 0

    cursor.execute("""
        SELECT category, description, amount, date, time
        FROM transactions
        WHERE user_id=%s AND year=%s AND month=%s AND transaction_type='Expense'
        ORDER BY date DESC
    """, (session['user_id'], year, month))
    expenses = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        total_income=total_income,
        expenses=expenses,
        month=month,
        year=year
    )

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect('/login')  # If not logged in, redirect to login page

    if request.method == 'POST':
        # Fetch data from the form
        category = request.form['category']
        description = request.form['description']
        amount = request.form['amount']
        date = datetime.now().date()
        time = datetime.now().time()

        # Get user ID
        user_id = session['user_id']
        month = session.get('selected_month')
        year = session.get('selected_year')

        # Insert the expense into the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user_id, transaction_type, category, description, amount, month, year, date, time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, 'Expense', category, description, amount, month, year, date, time))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Expense added successfully!")
        return redirect('/dashboard')  # Redirect back to the dashboard

    return render_template('add_expense.html')  # Render the form to add an expense

@app.route('/clear_transactions', methods=['POST'])
def clear_transactions():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete all transactions for the current user
    cursor.execute("DELETE FROM transactions WHERE user_id = %s", (session['user_id'],))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/summary')  # Redirect back to the summary page

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')
    return render_template('admin_dashboard.html')

@app.route('/admin/users')
def view_all_users():
    db = mysql.connector.connect(host='DB_HOST', user='DB_USER', password='DB_PASS', database='DB_NAME')
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, role FROM users")
    users = cursor.fetchall()
    db.close()
    return render_template('admin_users.html', users=users)


@app.route('/admin/analytics')
def admin_analytics():
    try:
        db = mysql.connector.connect(
            host='DB_HOST',
            user='DB_USER',
            password='DB_PASS',
            database='DB_NAME'
        )
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                u.id AS user_id,
                u.name,
                u.email,
                t.month,
                t.year,
                SUM(CASE WHEN t.transaction_type = 'Income' THEN t.amount ELSE 0 END) AS total_income,
                SUM(CASE WHEN t.transaction_type = 'Expense' THEN t.amount ELSE 0 END) AS total_expense,
                SUM(CASE WHEN t.transaction_type = 'Income' THEN t.amount ELSE 0 END) -
                SUM(CASE WHEN t.transaction_type = 'Expense' THEN t.amount ELSE 0 END) AS savings
            FROM users u
            LEFT JOIN transactions t ON u.id = t.user_id
            GROUP BY u.id, t.month, t.year
            ORDER BY t.year DESC, t.month DESC
        """)
        data = cursor.fetchall()
        db.close()

        return render_template('admin_analytics.html', data=data)

    except mysql.connector.Error as err:
        return f"Database error: {err}"


@app.route('/admin/user_transactions/<email>')
def user_transactions(email):
    db = mysql.connector.connect(host='localhost', user='root', password='Ananya9481005587', database='finance_management')
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        return "User not found", 404

    cursor.execute("SELECT * FROM transactions WHERE user_id = %s ORDER BY date DESC", (user['id'],))
    transactions = cursor.fetchall()
    db.close()

    return render_template('admin_user_transactions.html', email=email, transactions=transactions)

@app.route('/admin/user/<int:user_id>/transactions')
def view_user_transactions(user_id):
    try:
        db = mysql.connector.connect(
            host='DB_HOST',
            user='DB_USER',
            password='DB_PASS',
            database='DB_NAME'
        )
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT t.id, t.amount, t.category, t.transaction_type, t.date, t.month, t.year
            FROM transactions t
            WHERE t.user_id = %s
            ORDER BY t.date DESC
        """, (user_id,))
        transactions = cursor.fetchall()

        cursor.execute("SELECT name FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        db.close()

        return render_template('admin_user_transactions.html', transactions=transactions, user=user)

    except mysql.connector.Error as err:
        return f"Database error: {err}"
    
@app.route('/admin/create_user', methods=['GET', 'POST'])
def admin_create_user():  # Renamed to avoid conflict
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = mysql.connector.connect(
            host='DB_HOST',
            user='DB_USER',
            password='DB_PASS',
            database='DB_NAME'
        )
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                       (name, email, password, role))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/admin/users')
    
    return render_template('admin_create_user.html')

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        conn = mysql.connector.connect(
            host='DB_HOST',
            user='DB_USER',
            password='DB_PASS',
            database='DB_NAME'
        )
        cursor = conn.cursor()

        # Check if the user is an admin
        cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()

        if result and result[0] == 'admin':
            flash("You cannot delete admin users.")
        else:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            flash("User deleted successfully.")

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        flash(f"Database error: {err}")

    return redirect('/admin/users')


@app.route('/goal', methods=['GET', 'POST'])
def set_goal():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        goal_name = request.form['goal_name']
        goal_amount = request.form['goal_amount']
        current_amount = request.form['current_amount']
        target_date = request.form['target_date']  # Format should be YYYY-MM-DD

        cursor.execute("""
            INSERT INTO goals (user_id, goal_name, goal_amount, current_amount, target_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (session['user_id'], goal_name, goal_amount, current_amount, target_date))

        conn.commit()
        flash("Goal added successfully!")

    # Fetch goals for current user
    cursor.execute("SELECT * FROM goals WHERE user_id = %s", (session['user_id'],))
    user_goals = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('set_goal.html', goals=user_goals)

@app.route('/edit_goal/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    if 'user_id' not in session or session['role'] != 'user':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        goal_name = request.form['goal_name']
        goal_amount = request.form['goal_amount']
        current_amount = request.form['current_amount']
        target_date = request.form['target_date']

        cursor.execute("""
            UPDATE goals 
            SET goal_name=%s, goal_amount=%s, current_amount=%s, target_date=%s
            WHERE id=%s AND user_id=%s
        """, (goal_name, goal_amount, current_amount, target_date, goal_id, session['user_id']))
        conn.commit()
        flash("Goal updated successfully!")
        return redirect('/goal')

    # Get existing goal data
    cursor.execute("SELECT * FROM goals WHERE id = %s AND user_id = %s", (goal_id, session['user_id']))
    goal = cursor.fetchone()
    cursor.close()
    conn.close()

    if not goal:
        flash("Goal not found.")
        return redirect('/goal')

    return render_template('edit_goal.html', goal=goal)

@app.route('/delete_goal/<int:goal_id>')
def delete_goal(goal_id):
    if 'user_id' not in session or session['role'] != 'user':
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM goals WHERE id = %s AND user_id = %s", (goal_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Goal deleted successfully.")
    return redirect('/goal')

@app.route('/goal_success')
def goal_success():
    if 'user_id' not in session or session['role'] != 'user':
        flash('You need to log in as a user to access this page.', 'error')
        return redirect('/login')
    
    flash('Your goal has been set successfully!', 'success')
    return render_template('goal_success.html')

@app.route('/goal_error')
def goal_error():
    if 'user_id' not in session or session['role'] != 'user':
        flash('You need to log in as a user to access this page.', 'error')
        return redirect('/login')
    flash('An error occurred while setting your goal. Please try again.', 'error')
    return render_template('goal_error.html')

@app.route('/bills', methods=['GET', 'POST'])
def manage_bills():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        bill_name = request.form['bill_name']
        amount = request.form['amount']
        due_date = request.form['due_date']
        cursor.execute("""
            INSERT INTO bills (user_id, bill_name, amount, due_date)
            VALUES (%s, %s, %s, %s)
        """, (user_id, bill_name, amount, due_date))
        conn.commit()
        flash('Bill added successfully.')

    cursor.execute("SELECT * FROM bills WHERE user_id = %s ORDER BY due_date", (user_id,))
    bills = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('bills.html', bills=bills)


@app.route('/bill/delete/<int:bill_id>', methods=['POST'])
def delete_bill(bill_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bills WHERE id = %s AND user_id = %s", (bill_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Bill deleted.')
    return redirect('/bills')


@app.route('/bill/toggle/<int:bill_id>', methods=['POST'])
def toggle_bill_status(bill_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE bills
        SET is_paid = NOT is_paid
        WHERE id = %s AND user_id = %s
    """, (bill_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Bill status updated.')
    return redirect('/bills')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/error')
def error():
    flash('An unexpected error occurred. Please try again later.', 'error')
    return render_template('error.html')

if __name__ == "__main__":
    app.run(debug=True)

