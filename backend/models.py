"""Database models for SQLite."""
import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from config import DATABASE_PATH, API_KEY_LENGTH, API_KEY_PREFIX


class Database:
    """Database connection and initialization."""
    
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database tables."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        
        # API keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key_hash TEXT NOT NULL,
                name TEXT,
                created_at TEXT NOT NULL,
                last_used TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        # Machines table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                api_key_id INTEGER,
                name TEXT,
                last_seen TEXT,
                status TEXT DEFAULT 'offline',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL
            )
        ''')
        
        # Peripherals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS peripherals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT,
                location TEXT,
                last_updated TEXT NOT NULL,
                FOREIGN KEY (machine_id) REFERENCES machines(id) ON DELETE CASCADE,
                UNIQUE(machine_id, name)
            )
        ''')
        
        # Routes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                source_peripheral_id INTEGER NOT NULL,
                dest_peripheral_id INTEGER NOT NULL,
                item_filter TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (source_peripheral_id) REFERENCES peripherals(id) ON DELETE CASCADE,
                FOREIGN KEY (dest_peripheral_id) REFERENCES peripherals(id) ON DELETE CASCADE
            )
        ''')
        
        # Route items table (for specific item filters)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS route_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create default admin user if no users exist
        self._create_default_admin()
    
    def _create_default_admin(self):
        """Create default admin user if database is empty."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            default_password_hash = generate_password_hash('admin')
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin, created_at)
                VALUES (?, ?, ?, ?)
            ''', ('admin', default_password_hash, 1, datetime.utcnow().isoformat()))
            conn.commit()
        conn.close()


class User:
    """User model."""
    
    @staticmethod
    def create(username, password, is_admin=False):
        """Create a new user."""
        from werkzeug.security import generate_password_hash
        conn = Database().get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin, created_at)
                VALUES (?, ?, ?, ?)
            ''', (username, generate_password_hash(password), 1 if is_admin else 0, datetime.utcnow().isoformat()))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()
    
    @staticmethod
    def get_by_username(username):
        """Get user by username."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def verify_password(user, password):
        """Verify user password."""
        from werkzeug.security import check_password_hash
        return check_password_hash(user['password_hash'], password)


class APIKey:
    """API key model."""
    
    @staticmethod
    def generate_key():
        """Generate a new API key."""
        key = secrets.token_urlsafe(API_KEY_LENGTH)
        return f"{API_KEY_PREFIX}{key}"
    
    @staticmethod
    def hash_key(key):
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def create(user_id, name=None):
        """Create a new API key for a user."""
        key = APIKey.generate_key()
        key_hash = APIKey.hash_key(key)
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO api_keys (user_id, key_hash, name, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, key_hash, name, datetime.utcnow().isoformat()))
        conn.commit()
        key_id = cursor.lastrowid
        conn.close()
        return key, key_id
    
    @staticmethod
    def verify(key):
        """Verify an API key and return user info."""
        key_hash = APIKey.hash_key(key)
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT api_keys.*, users.id as user_id, users.username, users.is_admin
            FROM api_keys
            JOIN users ON api_keys.user_id = users.id
            WHERE api_keys.key_hash = ?
        ''', (key_hash,))
        row = cursor.fetchone()
        if row:
            # Update last_used
            cursor.execute('''
                UPDATE api_keys SET last_used = ? WHERE id = ?
            ''', (datetime.utcnow().isoformat(), row['id']))
            conn.commit()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_user(user_id):
        """Get all API keys for a user."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM api_keys WHERE user_id = ? ORDER BY created_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


class Machine:
    """Machine model."""
    
    @staticmethod
    def register(user_id, api_key_id, name):
        """Register or update a machine."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        
        # Check if machine already exists for this user and API key
        cursor.execute('''
            SELECT * FROM machines WHERE user_id = ? AND api_key_id = ?
        ''', (user_id, api_key_id))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing machine
            cursor.execute('''
                UPDATE machines 
                SET last_seen = ?, status = 'online', name = ?
                WHERE id = ?
            ''', (datetime.utcnow().isoformat(), name, existing['id']))
            machine_id = existing['id']
        else:
            # Create new machine
            cursor.execute('''
                INSERT INTO machines (user_id, api_key_id, name, last_seen, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, api_key_id, name, datetime.utcnow().isoformat(), 'online'))
            machine_id = cursor.lastrowid
        
        # Get the machine record
        cursor.execute('SELECT * FROM machines WHERE id = ?', (machine_id,))
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        return dict(row) if row else None
    
    @staticmethod
    def get_by_user(user_id):
        """Get all machines for a user."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM machines WHERE user_id = ? ORDER BY last_seen DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def update_status(machine_id, status):
        """Update machine status."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE machines SET status = ?, last_seen = ? WHERE id = ?
        ''', (status, datetime.utcnow().isoformat(), machine_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_id(machine_id):
        """Get machine by ID."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM machines WHERE id = ?', (machine_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


class Peripheral:
    """Peripheral model."""
    
    @staticmethod
    def register(machine_id, name, type_name=None, location=None):
        """Register or update a peripheral."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO peripherals (machine_id, name, type, location, last_updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(machine_id, name) DO UPDATE SET
                type = excluded.type,
                location = excluded.location,
                last_updated = excluded.last_updated
        ''', (machine_id, name, type_name, location, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_machine(machine_id):
        """Get all peripherals for a machine."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM peripherals WHERE machine_id = ? ORDER BY name
        ''', (machine_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_user(user_id):
        """Get all peripherals for a user's machines."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, m.name as machine_name, m.user_id
            FROM peripherals p
            JOIN machines m ON p.machine_id = m.id
            WHERE m.user_id = ?
            ORDER BY m.name, p.name
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_by_id(peripheral_id):
        """Get peripheral by ID."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM peripherals WHERE id = ?', (peripheral_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


class Route:
    """Route model."""
    
    @staticmethod
    def create(user_id, name, source_peripheral_id, dest_peripheral_id, item_filter=None, item_names=None):
        """Create a new route."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO routes (user_id, name, source_peripheral_id, dest_peripheral_id, item_filter, enabled, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, source_peripheral_id, dest_peripheral_id, item_filter, 1, datetime.utcnow().isoformat()))
        route_id = cursor.lastrowid
        
        # Add specific item names if provided
        if item_names:
            for item_name in item_names:
                cursor.execute('''
                    INSERT INTO route_items (route_id, item_name)
                    VALUES (?, ?)
                ''', (route_id, item_name))
        
        conn.commit()
        conn.close()
        return route_id
    
    @staticmethod
    def get_by_user(user_id):
        """Get all routes for a user."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, 
                   sp.name as source_name, sp.machine_id as source_machine_id,
                   dp.name as dest_name, dp.machine_id as dest_machine_id
            FROM routes r
            JOIN peripherals sp ON r.source_peripheral_id = sp.id
            JOIN peripherals dp ON r.dest_peripheral_id = dp.id
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        
        # Get item names for each route
        routes = []
        for row in rows:
            route = dict(row)
            cursor.execute('SELECT item_name FROM route_items WHERE route_id = ?', (route['id'],))
            route['item_names'] = [r['item_name'] for r in cursor.fetchall()]
            routes.append(route)
        
        conn.close()
        return routes
    
    @staticmethod
    def get_by_machine(machine_id):
        """Get all active routes involving a machine."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, 
                   sp.name as source_name, sp.machine_id as source_machine_id,
                   dp.name as dest_name, dp.machine_id as dest_machine_id
            FROM routes r
            JOIN peripherals sp ON r.source_peripheral_id = sp.id
            JOIN peripherals dp ON r.dest_peripheral_id = dp.id
            WHERE (sp.machine_id = ? OR dp.machine_id = ?) AND r.enabled = 1
            ORDER BY r.created_at DESC
        ''', (machine_id, machine_id))
        rows = cursor.fetchall()
        
        routes = []
        for row in rows:
            route = dict(row)
            cursor.execute('SELECT item_name FROM route_items WHERE route_id = ?', (route['id'],))
            route['item_names'] = [r['item_name'] for r in cursor.fetchall()]
            routes.append(route)
        
        conn.close()
        return routes
    
    @staticmethod
    def update(route_id, name=None, source_peripheral_id=None, dest_peripheral_id=None, 
               item_filter=None, enabled=None, item_names=None):
        """Update a route."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if source_peripheral_id is not None:
            updates.append('source_peripheral_id = ?')
            params.append(source_peripheral_id)
        if dest_peripheral_id is not None:
            updates.append('dest_peripheral_id = ?')
            params.append(dest_peripheral_id)
        if item_filter is not None:
            updates.append('item_filter = ?')
            params.append(item_filter)
        if enabled is not None:
            updates.append('enabled = ?')
            params.append(enabled)
        
        if updates:
            params.append(route_id)
            cursor.execute(f'UPDATE routes SET {", ".join(updates)} WHERE id = ?', params)
        
        # Update item names
        if item_names is not None:
            cursor.execute('DELETE FROM route_items WHERE route_id = ?', (route_id,))
            for item_name in item_names:
                cursor.execute('INSERT INTO route_items (route_id, item_name) VALUES (?, ?)', (route_id, item_name))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def delete(route_id):
        """Delete a route."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM routes WHERE id = ?', (route_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_id(route_id):
        """Get route by ID."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, 
                   sp.name as source_name, sp.machine_id as source_machine_id,
                   dp.name as dest_name, dp.machine_id as dest_machine_id
            FROM routes r
            JOIN peripherals sp ON r.source_peripheral_id = sp.id
            JOIN peripherals dp ON r.dest_peripheral_id = dp.id
            WHERE r.id = ?
        ''', (route_id,))
        row = cursor.fetchone()
        if row:
            route = dict(row)
            cursor.execute('SELECT item_name FROM route_items WHERE route_id = ?', (route_id,))
            route['item_names'] = [r['item_name'] for r in cursor.fetchall()]
            conn.close()
            return route
        conn.close()
        return None

