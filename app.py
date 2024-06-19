import os

from flask import Flask
from flask_login import LoginManager

from db import db
from routes import recipe_blueprint

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

db.init_app(app)  # Initialize the db with the app


# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Define the user_loader function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register the blueprint
app.register_blueprint(recipe_blueprint)

if __name__ == '__main__':
    # Import models to ensure they are registered with SQLAlchemy
    from models import Recipe, User

    # Create the database tables
    with app.app_context():
        db.create_all()
    app.run(debug=True)
