"""API routes and endpoints."""
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for
from models import User, APIKey, Machine, Peripheral, Route, Database
from auth import login_required, admin_required, api_key_required, verify_password
from item_filter import fuzzy_match_item, filter_items_by_name, get_common_minecraft_items
from datetime import datetime
import json

api = Blueprint('api', __name__, url_prefix='/api')
web = Blueprint('web', __name__)


# ==================== Web Routes ====================

@web.route('/')
def index():
    """Redirect to login or dashboard."""
    if 'user_id' in session:
        user = User.get_by_id(session['user_id'])
        if user and user['is_admin']:
            return redirect(url_for('web.admin'))
        return redirect(url_for('web.dashboard'))
    return redirect(url_for('web.login'))


@web.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = verify_password(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            if user['is_admin']:
                return redirect(url_for('web.admin'))
            return redirect(url_for('web.dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')


@web.route('/logout')
def logout():
    """Logout."""
    session.clear()
    return redirect(url_for('web.login'))


@web.route('/static/install.lua')
def serve_install_script():
    """Serve the install.lua script for wget."""
    import os
    from pathlib import Path
    from flask import send_from_directory
    
    base_dir = Path(__file__).parent.parent
    install_path = base_dir / 'computercraft' / 'install.lua'
    
    if install_path.exists():
        return send_from_directory(str(install_path.parent), 'install.lua', mimetype='text/plain')
    else:
        return "File not found", 404


@web.route('/static/transporter.lua')
def serve_transporter_script():
    """Serve the transporter.lua script for wget."""
    import os
    from pathlib import Path
    from flask import send_from_directory
    
    base_dir = Path(__file__).parent.parent
    transporter_path = base_dir / 'computercraft' / 'transporter.lua'
    
    if transporter_path.exists():
        return send_from_directory(str(transporter_path.parent), 'transporter.lua', mimetype='text/plain')
    else:
        return "File not found", 404


@web.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    user_id = session['user_id']
    return render_template('dashboard.html')


@web.route('/admin')
@login_required
@admin_required
def admin():
    """Admin dashboard."""
    return render_template('admin.html')


# ==================== API Routes for Web Interface ====================

@api.route('/users', methods=['GET'])
@login_required
@admin_required
def list_users():
    """List all users (admin only)."""
    conn = Database().get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, is_admin, created_at FROM users ORDER BY created_at DESC')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users)


@api.route('/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create a new user (admin only)."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user_id = User.create(username, password, is_admin)
    if user_id:
        return jsonify({'id': user_id, 'username': username}), 201
    return jsonify({'error': 'Username already exists'}), 400


@api.route('/user/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info."""
    user = User.get_by_id(session['user_id'])
    if user:
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'is_admin': bool(user['is_admin'])
        })
    return jsonify({'error': 'User not found'}), 404


@api.route('/users/<int:user_id>/password', methods=['PUT'])
@login_required
def change_password(user_id):
    """Change user password."""
    # Users can only change their own password, unless they're admin
    if user_id != session['user_id'] and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Old and new password required'}), 400
    
    if len(new_password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Verify old password
    if not User.verify_password(user, old_password):
        return jsonify({'error': 'Incorrect current password'}), 400
    
    # Update password
    from werkzeug.security import generate_password_hash
    conn = Database().get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET password_hash = ? WHERE id = ?
    ''', (generate_password_hash(new_password), user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@api.route('/api_keys', methods=['GET'])
@login_required
def list_api_keys():
    """List API keys for current user."""
    user_id = session['user_id']
    keys = APIKey.get_by_user(user_id)
    # Don't return the actual key hashes
    for key in keys:
        del key['key_hash']
    return jsonify(keys)


@api.route('/api_keys', methods=['POST'])
@login_required
def create_api_key():
    """Generate a new API key for current user."""
    user_id = session['user_id']
    data = request.json or {}
    name = data.get('name', 'New API Key')
    
    key, key_id = APIKey.create(user_id, name)
    return jsonify({'id': key_id, 'key': key, 'name': name}), 201


@api.route('/api_keys/<int:key_id>', methods=['DELETE'])
@login_required
def delete_api_key(key_id):
    """Delete (invalidate) an API key."""
    user_id = session['user_id']
    
    # Get the key to verify ownership
    conn = Database().get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM api_keys WHERE id = ? AND user_id = ?', (key_id, user_id))
    key = cursor.fetchone()
    
    if not key:
        conn.close()
        return jsonify({'error': 'API key not found or unauthorized'}), 404
    
    # Delete the key
    cursor.execute('DELETE FROM api_keys WHERE id = ?', (key_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@api.route('/machines', methods=['GET'])
@login_required
def list_machines():
    """List machines for current user."""
    user_id = session['user_id']
    machines = Machine.get_by_user(user_id)
    return jsonify(machines)


@api.route('/peripherals', methods=['GET'])
@login_required
def list_peripherals():
    """List peripherals for current user."""
    user_id = session['user_id']
    peripherals = Peripheral.get_by_user(user_id)
    return jsonify(peripherals)


@api.route('/peripherals/search', methods=['POST'])
@login_required
def search_peripherals():
    """Search peripherals with fuzzy matching."""
    user_id = session['user_id']
    data = request.json
    query = data.get('query', '')
    
    peripherals = Peripheral.get_by_user(user_id)
    if query:
        # Filter peripherals by name
        filtered = [p for p in peripherals if query.lower() in p['name'].lower()]
        return jsonify(filtered)
    return jsonify(peripherals)


@api.route('/items/search', methods=['POST'])
@login_required
def search_items():
    """Search for items with fuzzy matching."""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify([])
    
    # Get common items (in production, this might come from a database or mod data)
    common_items = get_common_minecraft_items()
    matches = filter_items_by_name(query, common_items)
    return jsonify(matches[:20])  # Limit to 20 results


@api.route('/routes', methods=['GET'])
@login_required
def list_routes():
    """List routes for current user."""
    user_id = session['user_id']
    routes = Route.get_by_user(user_id)
    return jsonify(routes)


@api.route('/routes', methods=['POST'])
@login_required
def create_route():
    """Create a new route."""
    user_id = session['user_id']
    data = request.json
    
    name = data.get('name')
    source_peripheral_id = data.get('source_peripheral_id')
    dest_peripheral_id = data.get('dest_peripheral_id')
    item_filter = data.get('item_filter')
    item_names = data.get('item_names', [])
    
    if not name or not source_peripheral_id or not dest_peripheral_id:
        return jsonify({'error': 'Name, source, and destination required'}), 400
    
    # Verify peripherals belong to user
    source = Peripheral.get_by_id(source_peripheral_id)
    dest = Peripheral.get_by_id(dest_peripheral_id)
    if not source or not dest:
        return jsonify({'error': 'Invalid peripheral'}), 400
    
    # Check machine ownership
    source_machine = Machine.get_by_id(source['machine_id'])
    dest_machine = Machine.get_by_id(dest['machine_id'])
    if not source_machine or not dest_machine:
        return jsonify({'error': 'Invalid machine'}), 400
    
    if source_machine['user_id'] != user_id or dest_machine['user_id'] != user_id:
        return jsonify({'error': 'Peripherals must belong to your machines'}), 403
    
    route_id = Route.create(user_id, name, source_peripheral_id, dest_peripheral_id, item_filter, item_names)
    route = Route.get_by_id(route_id)
    return jsonify(route), 201


@api.route('/routes/<int:route_id>', methods=['PUT'])
@login_required
def update_route(route_id):
    """Update a route."""
    user_id = session['user_id']
    route = Route.get_by_id(route_id)
    
    if not route:
        return jsonify({'error': 'Route not found'}), 404
    
    # Verify ownership
    source = Peripheral.get_by_id(route['source_peripheral_id'])
    if not source:
        return jsonify({'error': 'Invalid route'}), 400
    source_machine = Machine.get_by_id(source['machine_id'])
    if source_machine['user_id'] != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    Route.update(
        route_id,
        name=data.get('name'),
        source_peripheral_id=data.get('source_peripheral_id'),
        dest_peripheral_id=data.get('dest_peripheral_id'),
        item_filter=data.get('item_filter'),
        enabled=data.get('enabled'),
        item_names=data.get('item_names')
    )
    
    updated_route = Route.get_by_id(route_id)
    return jsonify(updated_route)


@api.route('/routes/<int:route_id>', methods=['DELETE'])
@login_required
def delete_route(route_id):
    """Delete a route."""
    user_id = session['user_id']
    route = Route.get_by_id(route_id)
    
    if not route:
        return jsonify({'error': 'Route not found'}), 404
    
    # Verify ownership
    source = Peripheral.get_by_id(route['source_peripheral_id'])
    if not source:
        return jsonify({'error': 'Invalid route'}), 400
    source_machine = Machine.get_by_id(source['machine_id'])
    if source_machine['user_id'] != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    Route.delete(route_id)
    return jsonify({'success': True})


# ==================== API Routes for ComputerCraft Machines ====================

@api.route('/auth', methods=['POST'])
@api_key_required
def cc_auth():
    """Authenticate CC machine and register it."""
    try:
        data = request.json or {}
        machine_name = data.get('name', 'Unknown Machine')
        
        machine = Machine.register(request.api_user_id, request.api_key_id, machine_name)
        
        if not machine:
            return jsonify({'error': 'Failed to register machine'}), 500
        
        return jsonify({
            'machine_id': machine['id'],
            'status': 'authenticated'
        })
    except Exception as e:
        import traceback
        print(f"Error in cc_auth: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@api.route('/peripherals', methods=['POST'])
@api_key_required
def cc_register_peripherals():
    """Register peripherals from CC machine."""
    data = request.json or {}
    machine_id = data.get('machine_id')
    peripherals = data.get('peripherals', [])
    
    if not machine_id:
        return jsonify({'error': 'machine_id required'}), 400
    
    # Verify machine belongs to user
    machine = Machine.get_by_id(machine_id)
    if not machine or machine['user_id'] != request.api_user_id:
        return jsonify({'error': 'Invalid machine'}), 403
    
    # Register each peripheral
    for peripheral_data in peripherals:
        Peripheral.register(
            machine_id,
            peripheral_data.get('name'),
            peripheral_data.get('type'),
            peripheral_data.get('location')
        )
    
    return jsonify({'success': True, 'registered': len(peripherals)})


@api.route('/routes', methods=['GET'])
@api_key_required
def cc_get_routes():
    """Get active routes for CC machine."""
    data = request.json or {}
    machine_id = data.get('machine_id')
    
    if not machine_id:
        return jsonify({'error': 'machine_id required'}), 400
    
    # Verify machine belongs to user
    machine = Machine.get_by_id(machine_id)
    if not machine or machine['user_id'] != request.api_user_id:
        return jsonify({'error': 'Invalid machine'}), 403
    
    routes = Route.get_by_machine(machine_id)
    return jsonify(routes)


@api.route('/commands', methods=['GET'])
@api_key_required
def cc_get_commands():
    """Poll for transport commands."""
    data = request.json or request.args
    machine_id = data.get('machine_id')
    
    if not machine_id:
        return jsonify({'error': 'machine_id required'}), 400
    
    # Verify machine belongs to user
    machine = Machine.get_by_id(machine_id)
    if not machine or machine['user_id'] != request.api_user_id:
        return jsonify({'error': 'Invalid machine'}), 403
    
    # Update machine status
    Machine.update_status(machine_id, 'online')
    
    # Get active routes for this machine
    routes = Route.get_by_machine(machine_id)
    
    # Format as commands
    commands = []
    for route in routes:
        commands.append({
            'route_id': route['id'],
            'action': 'transfer',
            'source': route['source_name'],
            'dest': route['dest_name'],
            'source_machine_id': route['source_machine_id'],
            'dest_machine_id': route['dest_machine_id'],
            'item_filter': route['item_filter'],
            'item_names': route.get('item_names', [])
        })
    
    return jsonify({'commands': commands})


@api.route('/status', methods=['POST'])
@api_key_required
def cc_update_status():
    """Update machine status."""
    data = request.json or {}
    machine_id = data.get('machine_id')
    status = data.get('status', 'online')
    
    if not machine_id:
        return jsonify({'error': 'machine_id required'}), 400
    
    # Verify machine belongs to user
    machine = Machine.get_by_id(machine_id)
    if not machine or machine['user_id'] != request.api_user_id:
        return jsonify({'error': 'Invalid machine'}), 403
    
    Machine.update_status(machine_id, status)
    return jsonify({'success': True})


@api.route('/machines/<int:machine_id>', methods=['DELETE'])
@login_required
def delete_machine(machine_id):
    """Deauthenticate/disconnect a machine."""
    user_id = session['user_id']
    machine = Machine.get_by_id(machine_id)
    
    if not machine:
        return jsonify({'error': 'Machine not found'}), 404
    
    # Verify ownership
    if machine['user_id'] != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Set machine status to offline and clear API key association
    from models import Database
    conn = Database().get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE machines 
        SET status = 'offline', api_key_id = NULL, last_seen = ?
        WHERE id = ?
    ''', (datetime.utcnow().isoformat(), machine_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})



