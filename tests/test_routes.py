import json

import pytest
from flask_login import login_user, logout_user

from ..app import app, db
from ..models import Recipe, User


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()

@pytest.fixture
def init_database():
    # Initialize the database with a user
    user = User(username='testuser', email='test@example.com')
    user.set_password('testpassword')
    db.session.add(user)
    db.session.commit()
    return user

def test_register_user(client, init_database):
    response = client.post('/api/users', json={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'newpassword'
    })
    assert response.status_code == 201  # Created
    # Decode the byte string to a regular string
    decoded_string = response.data.decode('utf-8')

    # Parse the string to a JSON object
    json_object = json.loads(decoded_string).get('message')
    assert 'User registered successfully' in json_object

def test_login_user(client, init_database):
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'testpassword'
    })
    assert response.status_code == 200
    assert b'Login successful' in response.data

# create test cases for recipe crete
def test_create_recipe(client, init_database):
    # Log in the user
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'testpassword'
    })
    assert response.status_code == 200
    assert b'Login successful' in response.data

    # Create a recipe
    response = client.post('/api/recipes', json={
        'title': 'Test Recipe',
        'description': 'Test Description',
        'ingredients': [{'name': 'Ingredient1', 'quantity': '1'}],
        'instructions': 'Test Instructions'
    })
    assert response.status_code == 201
    assert b'Recipe created successfully' in response.data

# create test cases for recipe get
def test_get_recipes(client, init_database):
    # Log in the user
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'testpassword'
    })
    assert response.status_code == 200
    assert b'Login successful' in response.data

    # Get all recipes
    response = client.get('/api/recipes')
    assert response.status_code == 200
    assert b'recipes' in response.data

# create test cases for recipe get single
def test_get_single_recipe(client, init_database):
    # Log in the user
    response = client.post('/api/login', json={
        'username': 'testuser',
        'password': 'testpassword'
    })
    assert response.status_code == 200
    assert b'Login successful' in response.data

    # Create a recipe
    recipe = Recipe(
        title='Test Recipe',
        description='Test Description',
        ingredients=json.dumps([{'name': 'Ingredient1', 'quantity': '1'}]),
        instructions='Test Instructions',
        user_id=init_database.id
    )
    db.session.add(recipe)
    db.session.commit()

    # Get the recipe using Session.get()
    recipe = db.session.get(Recipe, recipe.id)
    assert recipe is not None

    response = client.get(f'/api/recipes/{recipe.id}')
    assert response.status_code == 200


# create test cases for recipe update
def test_update_recipe(client, init_database):
    with client.session_transaction() as sess:
        with client.application.test_request_context():
            login_user(init_database)

    recipe = Recipe(
        title='Test Recipe',
        description='Test Description',
        ingredients=json.dumps([{'name': 'Ingredient1', 'quantity': '1'}]),
        instructions='Test Instructions',
        user_id=init_database.id
    )
    db.session.add(recipe)
    db.session.commit()

    response = client.put(f'/api/recipes/{recipe.id}', json={
        'title': 'Updated Recipe',
        'description': 'Updated Description',
        'ingredients': [{'name': 'Updated Ingredient', 'quantity': '2'}],
        'instructions': 'Updated Instructions'
    })
    assert response.status_code == 200
    assert b'Recipe updated successfully' in response.data

# create delete recipe test case
def test_delete_recipe(client, init_database):
    with client.session_transaction() as sess:
        with client.application.test_request_context():
            login_user(init_database)

    recipe = Recipe(
        title='Test Recipe',
        description='Test Description',
        ingredients=json.dumps([{'name': 'Ingredient1', 'quantity': '1'}]),
        instructions='Test Instructions',
        user_id=init_database.id
    )
    db.session.add(recipe)
    db.session.commit()

    response = client.delete(f'/api/recipes/{recipe.id}')
    assert response.status_code == 200
    assert b'Recipe deleted successfully' in response.data