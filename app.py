import os
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import utils  # Make sure you have your utils.py file!

# --- Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-super-long-and-random-secret-key-that-no-one-can-guess'
# Set up the SQLite database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'fin-trackr.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database extension
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # Redirects users to /login if they try to access a protected page
login_manager.login_message_category = 'info' # For flashing messages

# This 'user_loader' is required by Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    # This 'stocks' field is a "virtual" field
    # It links this User to all their Stock objects
    stocks = db.relationship('Stock', backref='owner', lazy=True)


# --- Database Model ---
class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Helper method (optional, but good to keep for future use)
    def to_dict(self):
        return {
            'id': self.id,
            'stock_name': self.stock_name,
            'quantity': self.quantity,
            'buy_price': self.buy_price,
            'current_price': self.current_price
        }

# --- Main Web Application Routes ---

@app.route('/')
def home():
    # This is your new public homepage
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        form_username = request.form['username']
        
        # --- VALIDATION CHECK ---
        # Check if username already exists in the database
        existing_user = User.query.filter_by(username=form_username).first()
        
        if existing_user:
            # If user exists, flash a 'danger' (red) message
            flash('That username is already taken. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        # --- END OF VALIDATION ---

        # If username is unique, proceed with creating the new user
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        new_user = User(
            username=form_username, 
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Flash a 'success' (green) message
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Find the user by their username
        user = User.query.filter_by(username=request.form['username']).first()
        
        # --- VALIDATION CHECK ---
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            # If both are correct, log them in
            login_user(user) 
            return redirect(url_for('portfolio')) # Send them to their portfolio
        else:
            
            flash('Invalid username or password. Please try again.', 'danger')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user() # Clears the user's session
    return redirect(url_for('home'))

@app.route('/portfolio', methods=['GET', 'POST'])
@login_required
def portfolio():
    # This block runs when the "Add Stock" form is submitted
    if request.method == 'POST':
        try:
            # Get all data from the form
            form_stock_name = request.form['stock_name'].upper() # Standardize name
            form_quantity = int(request.form['quantity'])
            form_buy_price = float(request.form['buy_price'])
            form_current_price = float(request.form['current_price']) # Get current price from form

            # Check if the user already owns this stock
            existing_stock = Stock.query.filter_by(
                user_id=current_user.id,
                stock_name=form_stock_name
            ).first()

            if existing_stock:
                # --- UPDATE EXISTING STOCK ---
                old_total_cost = existing_stock.quantity * existing_stock.buy_price
                new_purchase_cost = form_quantity * form_buy_price
                
                total_quantity = existing_stock.quantity + form_quantity
                new_average_price = (old_total_cost + new_purchase_cost) / total_quantity

                # Update the existing record with new average, new quantity, and new current price
                existing_stock.quantity = total_quantity
                existing_stock.buy_price = new_average_price
                existing_stock.current_price = form_current_price # <-- THIS IS THE UPDATE
                
                flash(f'Updated {form_stock_name} with {form_quantity} new shares.', 'success')
            else:
                # --- ADD NEW STOCK ---
                new_stock = Stock(
                    stock_name=form_stock_name,
                    quantity=form_quantity,
                    buy_price=form_buy_price,
                    current_price=form_current_price, # Use the price from the form
                    user_id=current_user.id
                )
                db.session.add(new_stock)
                flash(f'Added {form_stock_name} to your portfolio.', 'success')

            db.session.commit()
        except Exception as e:
            print(f"Error adding/updating stock: {e}")
            flash('Error processing your request. Please try again.', 'danger')
            
        return redirect(url_for('portfolio'))

    # --- THIS BLOCK RUNS FOR A GET REQUEST ---
    # (When the user just loads the page)
    all_stocks = Stock.query.filter_by(user_id=current_user.id).order_by(Stock.stock_name).all()
    
    # Call your utils function to do all the math
    portfolio_data, summary = utils.process_portfolio_data(all_stocks)
    
    # Send back the HTML page
    return render_template('portfolio.html', portfolio=portfolio_data, summary=summary)

@app.route('/manage_loss')
@login_required
def manage_loss():
    # Query for stocks that are currently at a loss
    losing_stocks = Stock.query.filter(
        Stock.user_id == current_user.id, 
        Stock.current_price < Stock.buy_price
    ).all()
    
    return render_template('manage_loss.html', losing_stocks=losing_stocks)

@app.route('/account')
@login_required
def account():
    # This page will show user details and the delete option
    return render_template('account.html')


@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    # This is a destructive action, so it must be a POST request

    # 1. First, delete all stocks owned by the user
    Stock.query.filter_by(user_id=current_user.id).delete()
    
    # 2. Then, delete the user themselves
    user_to_delete = User.query.get(current_user.id)
    db.session.delete(user_to_delete)
    
    # 3. Commit the changes
    db.session.commit()
    
    flash('Your account and all associated data have been permanently deleted.', 'success')
    return redirect(url_for('home'))


# Add this route to handle the calculation form
@app.route('/calculate_break_even', methods=['POST'])
@login_required
def calculate_break_even():
    try:
        stock_id = request.form['stock_id']
        p_target = float(request.form['p_target'])
        
        # Find the stock and make sure the logged-in user owns it
        stock = Stock.query.filter_by(id=stock_id, user_id=current_user.id).first_or_404()
        
        # Call your utils function
        q2 = utils.calculate_shares_to_buy(
            q1=stock.quantity,
            p1=stock.buy_price,
            p2=stock.current_price,
            p_target=p_target
        )
        
        return render_template('result.html', stock=stock, q2=q2, p_target=p_target)

    except Exception as e:
        print(f"Calculation Error: {e}")
        return redirect(url_for('manage_loss'))

    # This is the "Show Portfolio" logic
    
    # 3. CHANGE THE QUERY to get stocks for *this user only*
    all_stocks = Stock.query.filter_by(user_id=current_user.id).all()
    
    # Call your utils function (this part is the same)
    portfolio_data, summary = utils.process_portfolio_data(all_stocks)
    
    # 4. RENAME YOUR TEMPLATE
    return render_template('portfolio.html', portfolio=portfolio_data, summary=summary)


@app.route('/delete/<int:id>')
@login_required # <-- PROTECT THIS ROUTE
def delete_stock(id):
    # Find the stock, but also check that it belongs to the current user
    stock_to_delete = Stock.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(stock_to_delete)
        db.session.commit()
    except Exception as e:
        print(f"Error deleting stock: {e}")
        
    return redirect(url_for('portfolio'))


# --- Run the App ---
if __name__ == '__main__':
    # This block runs only when you execute 'python app.py'
    # It creates the 'fin-trackr.db' file and all tables
    # before starting the server.
    with app.app_context():
        db.create_all()
    
    app.run(debug=True) # debug=True reloads the server on changes