from flask import Flask, render_template, redirect, url_for, flash, request
import os
import requests # Add this import
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

# Determine the absolute path for the instance folder relative to app.py
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')

app = Flask(__name__, instance_path=instance_path)
app.config.from_object('flask_app.config') # Use full path for clarity and testability

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError: # Catch specific error for "directory exists"
    if not os.path.isdir(app.instance_path):
        raise
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'site.db')}"
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # type: ignore

class CSRFProtectForm(FlaskForm):
    pass

class RegistrationForm(CSRFProtectForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username): # type: ignore
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

class LoginForm(CSRFProtectForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CatalogSearchForm(CSRFProtectForm):
    query = StringField('Search Query', validators=[DataRequired()])
    submit = SubmitField('Search')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Hold(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.String(50), nullable=False) # Assuming item_id is a string like '1001'
    item_title = db.Column(db.String(200), nullable=True) # Store title for easier display
    placed_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('holds', lazy=True))

    def __repr__(self):
        return f"<Hold user_id={self.user_id} item_id='{self.item_id}' item_title='{self.item_title}'>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_mock_search_results(query: str):
    """
    Returns a list of mock book data based on a query.
    Ignores the query for now and returns a fixed list.
    """
    print(f"Mock API called with query: {query}") # Keep this for testing
    return [
        {'title': 'The Great Gatsby', 'creator': 'F. Scott Fitzgerald', 'id': '1001', 'type': {'name': 'Book'}},
        {'title': 'To Kill a Mockingbird', 'creator': 'Harper Lee', 'id': '1002', 'type': {'name': 'Book'}},
        {'title': '1984', 'creator': 'George Orwell', 'id': '1003', 'type': {'name': 'eBook'}},
        {'title': 'Pride and Prejudice', 'creator': 'Jane Austen', 'id': '1004', 'type': {'name': 'Book'}},
        {'title': 'The Hitchhiker\'s Guide to the Galaxy', 'creator': 'Douglas Adams', 'id': '1005', 'type': {'name': 'Audiobook'}},
    ]

@app.route('/')
def hello_world():
    return render_template('base.html', title='Home', content='Welcome to my Flask App!')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('hello_world'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data) # type: ignore
        user.set_password(form.password.data) # type: ignore
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('hello_world'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first() # type: ignore
        if user is None or not user.check_password(form.password.data): # type: ignore
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('hello_world'))
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('hello_world'))

@app.route('/search', methods=['GET', 'POST'])
@login_required # Re-enable login requirement
def search():
    form = CatalogSearchForm()
    results = []
    if form.validate_on_submit():
        query = form.query.data
        query_term = form.query.data

        # TODO: Replace this with a real API call when available
        # For now, use mock data
        results = get_mock_search_results(query_term) # type: ignore

        if not results:
            flash('No results found for your query.', 'info')

    return render_template('search_results.html', title='Search Results', form=form, results=results)

@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new tables."""
    with app.app_context():
        db.create_all()
    print("Initialized the database.")

@app.route('/hold/<item_id>', methods=['GET']) # Changed to GET to match link
@login_required
def place_hold(item_id):
    # TODO: When real API is used, might need to fetch item details by item_id
    # For now, we get item_title from query param for mock data
    item_title = request.args.get('item_title', 'Unknown Title')

    # Check if already on hold (optional, good practice)
    existing_hold = Hold.query.filter_by(user_id=current_user.id, item_id=item_id).first() # type: ignore
    if existing_hold:
        flash(f"You already have '{item_title}' on hold.", 'info')
    else:
        hold = Hold(user_id=current_user.id, item_id=item_id, item_title=item_title) # type: ignore
        db.session.add(hold)
        db.session.commit()
        flash(f"Successfully placed a hold for '{item_title}' (ID: {item_id}).", 'success')

    # Redirect back to search results, or home, or a new "My Holds" page
    # For simplicity, redirect to home for now.
    return redirect(url_for('hello_world'))

@app.route('/my-holds')
@login_required
def my_holds():
    holds = Hold.query.filter_by(user_id=current_user.id).order_by(Hold.placed_at.desc()).all() # type: ignore
    return render_template('my_holds.html', title='My Holds', holds=holds)

@app.route('/branches')
def branches():
    # TODO: Implement actual API call or fallback for branch information
    # For now, no API endpoint was found.
    # Using static sample data instead.
    sample_branches_data = [
        {
            'id': 'central',
            'name': 'Austin Central Library',
            'address': '710 W. Cesar Chavez St., Austin, TX 78701',
            'hours': 'Mon-Thu 10 AM - 9 PM, Fri-Sat 10 AM - 6 PM, Sun 12 PM - 6 PM',
            'phone': '512-974-7400',
            'website_link': 'https://library.austintexas.gov/central-library'
        },
        {
            'id': 'terrazas',
            'name': 'Terrazas Branch',
            'address': '1105 E. Cesar Chavez St., Austin, TX 78702',
            'hours': 'Mon-Thu 10 AM - 9 PM, Fri 10 AM - 6 PM, Sat 10 AM - 5 PM, Sun Closed',
            'phone': '512-974-3625',
            'website_link': 'https://library.austintexas.gov/terrazas-branch'
        },
        {
            'id': 'ruiz',
            'name': 'Ruiz Branch',
            'address': '1600 Grove Blvd., Austin, TX 78741',
            'hours': 'Mon-Thu 10 AM - 9 PM, Fri 10 AM - 6 PM, Sat 10 AM - 5 PM, Sun Closed',
            'phone': '512-974-7400', # Example, phone might be different
            'website_link': 'https://library.austintexas.gov/ruiz-branch'
        }
    ]
    # message = "Library branch information is currently unavailable. Please check back later."
    # Pass the static data to the template
    return render_template('branches.html', title='Library Branches', branches=sample_branches_data, message=None)

digital_resources_data = [
    {
        'id': 'overdrive',
        'name': 'OverDrive / Libby',
        'description': 'Access a wide range of eBooks, eAudiobooks, magazines, and streaming video.',
        'link': 'https://austinlibrary.overdrive.com/'
    },
    {
        'id': 'udemy',
        'name': 'Gale Presents: Udemy',
        'description': 'Thousands of on-demand video courses for upskilling in business, technology, design, and more.',
        # This is the direct link after APL's redirection
        'link': 'https://atxlibrary.idm.oclc.org/login?url=https://link.gale.com/apps/UDEMY?u=txshrpub100020'
    },
    {
        'id': 'brainfuse',
        'name': 'Brainfuse HelpNow',
        'description': 'Live online tutoring, homework help, test prep, and writing assistance for K-12 and adult learners.',
        'link': 'https://atxlibrary.idm.oclc.org/login?url=https://www.brainfuse.com/highed/helpNow.asp?a_id=BDD00FF9&ss=&r='
    },
    {
        'id': 'kanopy',
        'name': 'Kanopy',
        'description': 'Stream thousands of movies, documentaries, and acclaimed films.',
        'link': 'http://austinpl.kanopystreaming.com/'
    }
]

@app.route('/digital-resources')
def digital_resources():
    return render_template('digital_resources.html', title='Digital Resources', resources=digital_resources_data)

if __name__ == '__main__':
    app.run(debug=True)
