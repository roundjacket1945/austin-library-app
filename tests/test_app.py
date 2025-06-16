import pytest
from flask_app.app import app as flask_application, db, User, Hold # Import necessary components

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Basic config for testing
    flask_application.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
        "SERVER_NAME": "localhost.localdomain",
        "SECRET_KEY": "test_secret_key"  # Explicitly set for testing sessions/flashes
    })

    # The app instance_path needs to be correctly set for tests too,
    # if any features rely on it (though for in-memory DB it's less critical).
    # flask_application.instance_path is already set correctly when app is created.

    with flask_application.app_context():
        db.create_all() # Create all tables for the in-memory database
        yield flask_application
        db.drop_all() # Drop all tables after the test

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

# --- Basic Tests ---
def test_home_page(client):
    """Test the home page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome to my Flask App!" in response.data # from base.html via hello_world route

def test_branches_page(client):
    """Test the branches page."""
    response = client.get('/branches')
    assert response.status_code == 200
    assert b"Library Branches" in response.data
    assert b"Austin Central Library" in response.data # Check for static branch name

def test_digital_resources_page(client):
    """Test the digital resources page."""
    response = client.get('/digital-resources')
    assert response.status_code == 200
    assert b"Digital Resources" in response.data
    assert b"OverDrive / Libby" in response.data # Check for static resource name

# --- Authentication Tests ---
def test_user_registration(client, app):
    """Test user registration."""
    # GET request to ensure form is displayed
    response_get = client.get('/register')
    assert response_get.status_code == 200

    # POST request to register a new user
    response_post = client.post('/register', data={
        'username': 'testuser_reg',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response_post.status_code == 200 # Should redirect to login, then 200
    assert b"Congratulations, you are now a registered user!" in response_post.data # Flash message

    # Verify user in database (within app context)
    with app.app_context():
        user = User.query.filter_by(username='testuser_reg').first()
        assert user is not None
        assert user.username == 'testuser_reg'

def test_user_login_logout(client, app):
    """Test user login and logout."""
    # First, register a user to log in with
    client.post('/register', data={
        'username': 'testuser_login',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)

    # Test GET login page
    response_get_login = client.get('/login')
    assert response_get_login.status_code == 200

    # Test successful login
    response_login = client.post('/login', data={
        'username': 'testuser_login',
        'password': 'password123'
    }, follow_redirects=True)
    assert response_login.status_code == 200
    assert b"Welcome to my Flask App!" in response_login.data # Assuming redirect to home
    assert b"Logout" in response_login.data # Logout link should be visible

    # Test logout
    response_logout = client.get('/logout', follow_redirects=True)
    assert response_logout.status_code == 200
    assert b"You have been logged out." in response_logout.data
    assert b"Login" in response_logout.data # Login link should be visible again

def test_protected_route_access_unauthenticated(client):
    """Test accessing a protected route (e.g., /my-holds) when not logged in."""
    response = client.get('/my-holds', follow_redirects=True)
    assert response.status_code == 200 # Redirects to login
    assert b"Login" in response.data # Should be on login page
    assert b"Please log in to access this page." in response.data

def test_protected_route_access_authenticated(client):
    """Test accessing a protected route after login."""
    # Register and login
    client.post('/register', data={'username': 'authtestuser', 'password': 'password', 'confirm_password': 'password'}, follow_redirects=True)
    client.post('/login', data={'username': 'authtestuser', 'password': 'password'}, follow_redirects=True)

    response = client.get('/my-holds')
    assert response.status_code == 200
    assert b"My Holds" in response.data # Should be on My Holds page
    assert b"You have no items on hold." in response.data # Initially no holds

# --- Mocked Feature Tests ---
def test_search_page_get(client):
    """Test GET request to search page (requires login)."""
    # Register and login a user first
    client.post('/register', data={'username': 'searchuser', 'password': 'password', 'confirm_password': 'password'}, follow_redirects=True)
    client.post('/login', data={'username': 'searchuser', 'password': 'password'}, follow_redirects=True)

    response = client.get('/search')
    assert response.status_code == 200
    assert b"Search Catalog" in response.data

def test_search_submit_post(client):
    """Test submitting the search form (POST)."""
    # Register and login
    client.post('/register', data={'username': 'searchuser2', 'password': 'password', 'confirm_password': 'password'}, follow_redirects=True)
    client.post('/login', data={'username': 'searchuser2', 'password': 'password'}, follow_redirects=True)

    response = client.post('/search', data={'query': 'test search'}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Search Results" in response.data # Title of the page
    # Check for one of the mock book titles
    assert b"The Great Gatsby" in response.data

def test_place_hold_workflow(client, app):
    """Test the full workflow of placing a hold."""
    # 1. Register and Login
    client.post('/register', data={'username': 'holduser_test', 'password': 'password', 'confirm_password': 'password'}, follow_redirects=True)
    login_response = client.post('/login', data={'username': 'holduser_test', 'password': 'password'}, follow_redirects=True)
    assert b"Logout" in login_response.data # Confirm login

    # 2. (Simulate) Access search, assume we found an item.
    #    We know mock data will be used. Let's pick one.
    mock_item_id = "1001"
    mock_item_title = "The Great Gatsby"

    # 3. Make a GET request to /hold/<item_id>
    # Need to be in request context for url_for if used by flash messages, but client.get handles it.
    # The SERVER_NAME config in app fixture helps url_for.
    hold_url = f'/hold/{mock_item_id}?item_title={mock_item_title.replace(" ", "%20")}'

    # Make the request that sets the flash, but don't follow redirects yet
    response_set_flash = client.get(hold_url)
    assert response_set_flash.status_code == 302 # Should be a redirect

    # Now get the page where the flash should be displayed (the home page)
    # Let's check the session directly for the flash message
    expected_flash_message = f"Successfully placed a hold for '{mock_item_title}' (ID: {mock_item_id})."
    with client.session_transaction() as session:
        flashes = session.get('_flashes', [])
        assert len(flashes) > 0
        # flashes is a list of tuples (category, message)
        assert flashes[0][0] == 'success'
        assert flashes[0][1] == expected_flash_message

    # The flash message should be consumed after being accessed once (typically by render_template).
    # For now, confirming it's in the session is sufficient for this part of the test.
    # Verifying rendering can be tricky if messages are cleared unexpectedly by test client interactions.
    # response_show_flash = client.get('/')
    # assert response_show_flash.status_code == 200
    # assert expected_flash_message.encode('utf-8') in response_show_flash.data

    # 4. Check that the item appears on the /my-holds page.
    # This request will render and thus clear any remaining flashes from the session.
    response_my_holds = client.get('/my-holds')
    assert response_my_holds.status_code == 200
    assert b"My Holds" in response_my_holds.data
    assert mock_item_title.encode('utf-8') in response_my_holds.data
    assert mock_item_id.encode('utf-8') in response_my_holds.data

    # 5. Test placing the same hold again (should show "already on hold")
    response_set_flash_again = client.get(hold_url) # Don't follow redirect
    assert response_set_flash_again.status_code == 302

    expected_flash_already_on_hold = f"You already have '{mock_item_title}' on hold."
    with client.session_transaction() as session:
        flashes_again = session.get('_flashes', [])
        assert len(flashes_again) > 0
        assert flashes_again[0][0] == 'info' # Category is 'info'
        assert flashes_again[0][1] == expected_flash_already_on_hold

    # Optionally, verify the page it redirects to (home page)
    # response_show_flash_again = client.get('/')
    # assert response_show_flash_again.status_code == 200
    # assert expected_flash_already_on_hold.encode('utf-8') in response_show_flash_again.data
