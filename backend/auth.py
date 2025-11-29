"""Authentication and authorization utilities."""
from functools import wraps
from flask import session, request, jsonify
from models import User, APIKey


def login_required(f):
    """Decorator to require login for web routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        user = User.get_by_id(session['user_id'])
        if not user or not user['is_admin']:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def api_key_required(f):
    """Decorator to require valid API key for CC machine routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.json.get('api_key') if request.is_json else None
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        key_info = APIKey.verify(api_key)
        if not key_info:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Attach user info to request
        request.api_user_id = key_info['user_id']
        request.api_key_id = key_info['id']
        return f(*args, **kwargs)
    return decorated_function


def verify_password(username, password):
    """Verify user credentials."""
    user = User.get_by_username(username)
    if not user:
        return None
    if User.verify_password(user, password):
        return user
    return None

