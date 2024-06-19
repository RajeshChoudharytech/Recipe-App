import json

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user
from sqlalchemy import or_
from werkzeug.security import check_password_hash

from db import db
from models import Recipe, User
from schema import RecipeSchema, UserSchema

# Create a Blueprint instance
recipe_blueprint = Blueprint('recipe', __name__)

# Initialize schemas
user_schema = UserSchema()
recipe_schema = RecipeSchema()

# Create a user
@recipe_blueprint.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400

    # Check if username or email already exists
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return jsonify({'error': 'Username or email already exists'}), 400

    try:
        # Create a new user instance
        new_user = User(username=username, email=email)
        # Hash the password
        new_user.set_password(password)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User registered successfully'}), 201
    except Exception as e:
        # Rollback the transaction in case of any error
        db.session.rollback()
        return jsonify({'error': 'Failed to register user', 'details': str(e)}), 500

# login user
@recipe_blueprint.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    try:
        # Check if username and password are provided
        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400

        # Retrieve the user from the database
        user = User.query.filter_by(username=username).first()

        # Check if the user exists and the password is correct
        if user and check_password_hash(user.password, password):
            # Use Flask-Login to log in the user
            login_user(user)
            return jsonify({'message': 'Login successful'}), 200
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        return jsonify({'error': 'An error occurred while processing the request'}), 500

@recipe_blueprint.route('/api/recipes', methods=['POST'])
@login_required
def create_recipe():
    try:
        data = request.json
        # Check if required fields are provided
        if not all(key in data for key in ['title', 'instructions', 'ingredients']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if ingredients are provided and have both name and quantity
        if not all(('name' in ingredient and 'quantity' in ingredient) for ingredient in data['ingredients']):
            return jsonify({'error': 'All ingredients must have both name and quantity'}), 400

        # Convert ingredients to JSON string
        ingredients_json = json.dumps(data['ingredients'])
        # Create a new recipe object
        new_recipe = Recipe(
            title=data['title'],
            description=data.get('description', ''),
            ingredients=ingredients_json,  # Store as JSON string
            instructions=data['instructions'],
            user_id=current_user.id
        )
        db.session.add(new_recipe)
        db.session.commit()
        # Return the serialized recipe data as a JSON response
        return jsonify({'message': 'Recipe created successfully', 'recipe': recipe_schema.dump(new_recipe)}), 201
    except Exception as e:
        return jsonify({'error': 'An error occurred while processing the request'}), 500

# Get all recipes
@recipe_blueprint.route('/api/recipes', methods=['GET'])
@login_required
def get_recipes():
    try:
        # Get query parameters for search and pagination
        search_query = request.args.get('q', '')  # Default to empty string if 'q' parameter is not provided
        page = request.args.get('page', 1, type=int)  # Default to page 1 if 'page' parameter is not provided

        # Filter recipes based on the search query
        recipes_query = Recipe.query.filter(
            or_(Recipe.title.ilike(f'%{search_query}%'),  # Search by title
                Recipe.ingredients.ilike(f'%{search_query}%'))  # Search by ingredients
        )

        # Paginate the filtered recipes
        per_page = 10  # Number of recipes per page
        paginated_recipes = recipes_query.paginate(page=page, per_page=per_page)

        # Serialize the paginated recipes
        recipes = recipe_schema.dump(paginated_recipes.items, many=True)

        # Create pagination metadata
        pagination = {
            'total_pages': paginated_recipes.pages,
            'total_records': paginated_recipes.total,
            'current_page': paginated_recipes.page,
            'per_page': per_page
        }

        # Return the paginated recipes and pagination metadata as a JSON response
        return jsonify({'recipes': recipes, 'pagination': pagination}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while processing the request'}), 500

# Get a single recipe
@recipe_blueprint.route('/api/recipes/<int:recipe_id>', methods=['GET'])
@login_required
def get_recipe(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)

        # Check if the current user is the owner of the recipe
        if recipe.author != current_user:
            return jsonify({'error': 'You are not authorized to view this recipe'}), 403

        # Return the serialized recipe data as a JSON response
        return jsonify(recipe_schema.dump(recipe)), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while processing the request'}), 500

# Update a recipe
@recipe_blueprint.route('/api/recipes/<int:recipe_id>', methods=['PUT'])
@login_required
def update_recipe(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        data = request.json

        # Check if the current user is the owner of the recipe
        if recipe.author != current_user:
            return jsonify({'error': 'You are not authorized to update this recipe'}), 403

        # Check if required fields are provided
        if not all(key in data for key in ['title', 'instructions', 'ingredients']):
            return jsonify({'error': 'Missing required fields'}), 400

        # Check if ingredients are provided and have both name and quantity
        if not all(('name' in ingredient and 'quantity' in ingredient) for ingredient in data['ingredients']):
            return jsonify({'error': 'All ingredients must have both name and quantity'}), 400

        # Update recipe fields
        recipe.title = data['title']
        recipe.description = data.get('description', '')
        # Serialize ingredients JSON array to a string
        recipe.ingredients = json.dumps(data['ingredients'])
        recipe.instructions = data['instructions']
        db.session.commit()

        # Return the updated recipe data as a JSON response
        return jsonify({'message': 'Recipe updated successfully', 'recipe': recipe_schema.dump(recipe)}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while processing the request'}), 500

# Delete a recipe
@recipe_blueprint.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
@login_required
def delete_recipe(recipe_id):
    try:
        recipe = Recipe.query.get_or_404(recipe_id)
        
        # Check if the current user is the owner of the recipe
        if recipe.author != current_user:
            return jsonify({'error': 'You are not authorized to delete this recipe'}), 403

        db.session.delete(recipe)
        db.session.commit()
        return jsonify({'message': 'Recipe deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'An error occurred while deleting the recipe'}), 500
    
