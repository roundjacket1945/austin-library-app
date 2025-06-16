# Austin Public Library App

## Description

A Flask web application designed to simulate interaction with Austin Public Library services. This project was developed to demonstrate core web application features, including user authentication, data display, and interaction with external (mocked) services.

## Features

-   User registration and login/logout
-   Mocked library catalog search (displays a static list of books)
-   Mocked ability to place holds on library items
-   Page to view a user's currently placed holds
-   Static list of library branches with their details (address, hours, etc.)
-   Static list of digital resources with links to Austin Public Library's actual resource pages

## Setup and Running the Application

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd <project_directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    Ensure you have `pip` installed.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the database:**
    The application uses Flask-SQLAlchemy for database management. The database file (`site.db`) will be created in the `flask_app/instance/` directory.
    ```bash
    flask --app flask_app/app init-db
    ```
    Or, if the above gives issues depending on your environment setup for `FLASK_APP`:
    ```bash
    python -m flask --app flask_app/app init-db
    ```

5.  **Run the Flask development server:**
    ```bash
    flask --app flask_app/app run --debug
    ```
    Or, if you prefer to run directly via Python (which is how the `if __name__ == '__main__':` block is set up in `app.py`):
    ```bash
    python flask_app/app.py
    ```
    The application will typically be available at `http://127.0.0.1:5000/`.

## Configuration

-   **Secret Key & API Configuration:** Configuration variables, including the `SECRET_KEY` for session management and `APL_API_BASE`, are stored in `flask_app/config.py`.
-   The `APL_API_BASE` was initially intended for the Austin Public Library API. However, during development, suitable JSON API endpoints for catalog search and branch information were not found at this base URL. The catalog search functionality was found to be handled by Bibliocommons, which did not present an easily consumable JSON API.

## API Usage Notes

-   **Catalog Search & Place Holds:** The library catalog search and the ability to place holds are currently **mocked**. This means they use pre-defined, static data within the application rather than interacting with a live external API. This was done because a publicly accessible and usable JSON API for these services from Austin Public Library or its provider (Bibliocommons) was not identified during the development period.
-   **Branch Information:** The library branch information displayed on the "Branches" page is also **static data** hardcoded into the application. This is due to the same reasons mentioned above – no suitable JSON API endpoint for fetching live branch data was found.
-   **Digital Resources:** The "Digital Resources" page lists actual resources provided by APL and links directly to them.

This setup allows the application to demonstrate its features without requiring live external API access for the core library service simulations.
