// API Base URL
const API_BASE = '/api';

// Utility Functions
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const response = await fetch(url, { ...defaultOptions, ...options });
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'API request failed');
    }
    
    return data;
}

function showAlert(message, type = 'error') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    document.body.insertBefore(alert, document.body.firstChild);
    setTimeout(() => alert.remove(), 5000);
}

// Dashboard Functions
let selectedItems = [];
let peripherals = [];
let routes = [];

async function loadDashboard() {
    try {
        await Promise.all([
            loadAPIKeys(),
            loadMachines(),
            loadPeripherals(),
            loadRoutes()
        ]);
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showAlert('Failed to load dashboard data');
    }
}

async function loadAPIKeys() {
    try {
        const keys = await apiCall('/api_keys');
        const container = document.getElementById('api-keys-list');
        container.innerHTML = '';
        
        if (keys.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary);">No API keys yet. Generate one to connect your ComputerCraft machines.</p>';
            return;
        }
        
        keys.forEach(key => {
            const item = document.createElement('div');
            item.className = 'api-key-item';
            item.innerHTML = `
                <div>
                    <strong>${key.name || 'Unnamed Key'}</strong>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">
                        Created: ${new Date(key.created_at).toLocaleDateString()}
                        ${key.last_used ? ` • Last used: ${new Date(key.last_used).toLocaleDateString()}` : ' • Never used'}
                    </div>
                </div>
                <button class="btn btn-danger" onclick="deleteAPIKey(${key.id})" style="font-size: 0.875rem; padding: 0.5rem 1rem;">Invalidate</button>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading API keys:', error);
    }
}

async function createAPIKey() {
    const name = prompt('Enter a name for this API key:');
    if (!name) return;
    
    try {
        const result = await apiCall('/api_keys', {
            method: 'POST',
            body: JSON.stringify({ name })
        });
        
        // Show the key to the user (they need to copy it)
        const keyDisplay = prompt(
            'API Key generated! Copy this key now (it won\'t be shown again):\n\n' + result.key,
            result.key
        );
        
        await loadAPIKeys();
        showAlert('API key created successfully', 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

async function loadMachines() {
    try {
        const machines = await apiCall('/machines');
        const container = document.getElementById('machines-list');
        container.innerHTML = '';
        
        if (machines.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary);">No machines connected yet.</p>';
            return;
        }
        
        machines.forEach(machine => {
            const item = document.createElement('div');
            item.className = 'machine-item';
            const statusClass = machine.status === 'online' ? 'status-online' : 'status-offline';
            item.innerHTML = `
                <div>
                    <strong>${machine.name || 'Unnamed Machine'}</strong>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">
                        Last seen: ${machine.last_seen ? new Date(machine.last_seen).toLocaleString() : 'Never'}
                    </div>
                </div>
                <span class="status-badge ${statusClass}">${machine.status}</span>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading machines:', error);
    }
}

async function loadPeripherals() {
    try {
        peripherals = await apiCall('/peripherals');
        const container = document.getElementById('peripherals-list');
        container.innerHTML = '';
        
        if (peripherals.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary);">No peripherals discovered yet.</p>';
            return;
        }
        
        peripherals.forEach(peripheral => {
            const item = document.createElement('div');
            item.className = 'peripheral-item';
            item.innerHTML = `
                <div>
                    <strong>${peripheral.name}</strong>
                    <div style="font-size: 0.875rem; color: var(--text-secondary);">
                        ${peripheral.machine_name || 'Unknown Machine'} • ${peripheral.type || 'Unknown Type'}
                    </div>
                </div>
            `;
            container.appendChild(item);
        });
        
        // Update route form dropdowns
        updatePeripheralSelects();
    } catch (error) {
        console.error('Error loading peripherals:', error);
    }
}

function updatePeripheralSelects() {
    const sourceSelect = document.getElementById('source-peripheral');
    const destSelect = document.getElementById('dest-peripheral');
    
    [sourceSelect, destSelect].forEach(select => {
        select.innerHTML = '<option value="">Select peripheral...</option>';
        peripherals.forEach(p => {
            const option = document.createElement('option');
            option.value = p.id;
            option.textContent = `${p.machine_name} - ${p.name}`;
            select.appendChild(option);
        });
    });
}

async function loadRoutes() {
    try {
        routes = await apiCall('/routes');
        const container = document.getElementById('routes-list');
        container.innerHTML = '';
        
        if (routes.length === 0) {
            container.innerHTML = '<p style="color: var(--text-secondary);">No routes created yet.</p>';
            return;
        }
        
        routes.forEach(route => {
            const item = document.createElement('div');
            item.className = 'route-item';
            const enabledText = route.enabled ? 'Enabled' : 'Disabled';
            const enabledClass = route.enabled ? 'status-online' : 'status-offline';
            item.innerHTML = `
                <div class="route-item-header">
                    <div>
                        <strong>${route.name}</strong>
                        <div class="route-item-info">
                            ${route.source_name} → ${route.dest_name}
                            ${route.item_names && route.item_names.length > 0 ? `• ${route.item_names.length} items` : ''}
                        </div>
                    </div>
                    <div class="route-item-actions">
                        <span class="status-badge ${enabledClass}">${enabledText}</span>
                        <button class="btn btn-secondary" onclick="toggleRoute(${route.id}, ${!route.enabled})">
                            ${route.enabled ? 'Disable' : 'Enable'}
                        </button>
                        <button class="btn btn-danger" onclick="deleteRoute(${route.id})">Delete</button>
                    </div>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading routes:', error);
    }
}

// Route Management
function showCreateRouteModal() {
    document.getElementById('create-route-modal').classList.add('active');
    selectedItems = [];
    updateSelectedItems();
}

function closeCreateRouteModal() {
    document.getElementById('create-route-modal').classList.remove('active');
    document.getElementById('create-route-form').reset();
    selectedItems = [];
    updateSelectedItems();
    document.getElementById('item-suggestions').classList.remove('active');
}

// Item search with fuzzy matching
let itemSearchTimeout;
document.getElementById('item-filter')?.addEventListener('input', function(e) {
    clearTimeout(itemSearchTimeout);
    const query = e.target.value.trim();
    const suggestions = document.getElementById('item-suggestions');
    
    if (!query) {
        suggestions.classList.remove('active');
        return;
    }
    
    itemSearchTimeout = setTimeout(async () => {
        try {
            const matches = await apiCall('/items/search', {
                method: 'POST',
                body: JSON.stringify({ query })
            });
            
            suggestions.innerHTML = '';
            if (matches.length > 0) {
                matches.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'item-suggestion';
                    div.textContent = item;
                    div.onclick = () => addSelectedItem(item);
                    suggestions.appendChild(div);
                });
                suggestions.classList.add('active');
            } else {
                suggestions.classList.remove('active');
            }
        } catch (error) {
            console.error('Error searching items:', error);
        }
    }, 300);
});

function addSelectedItem(item) {
    if (!selectedItems.includes(item)) {
        selectedItems.push(item);
        updateSelectedItems();
        document.getElementById('item-filter').value = '';
        document.getElementById('item-suggestions').classList.remove('active');
    }
}

function removeSelectedItem(item) {
    selectedItems = selectedItems.filter(i => i !== item);
    updateSelectedItems();
}

function updateSelectedItems() {
    const container = document.getElementById('selected-items');
    container.innerHTML = '';
    selectedItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'selected-item';
        div.innerHTML = `
            ${item}
            <span class="selected-item-remove" onclick="removeSelectedItem('${item}')">×</span>
        `;
        container.appendChild(div);
    });
}

async function createRoute(event) {
    event.preventDefault();
    
    const name = document.getElementById('route-name').value;
    const sourceId = parseInt(document.getElementById('source-peripheral').value);
    const destId = parseInt(document.getElementById('dest-peripheral').value);
    const itemFilter = document.getElementById('item-filter').value;
    
    if (!name || !sourceId || !destId) {
        showAlert('Please fill in all required fields');
        return;
    }
    
    try {
        await apiCall('/routes', {
            method: 'POST',
            body: JSON.stringify({
                name,
                source_peripheral_id: sourceId,
                dest_peripheral_id: destId,
                item_filter: itemFilter || null,
                item_names: selectedItems.length > 0 ? selectedItems : null
            })
        });
        
        closeCreateRouteModal();
        await loadRoutes();
        showAlert('Route created successfully', 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

async function toggleRoute(routeId, enabled) {
    try {
        await apiCall(`/routes/${routeId}`, {
            method: 'PUT',
            body: JSON.stringify({ enabled })
        });
        await loadRoutes();
        showAlert(`Route ${enabled ? 'enabled' : 'disabled'}`, 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

async function deleteRoute(routeId) {
    if (!confirm('Are you sure you want to delete this route?')) return;
    
    try {
        await apiCall(`/routes/${routeId}`, {
            method: 'DELETE'
        });
        await loadRoutes();
        showAlert('Route deleted', 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

// Admin Functions
function showTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.admin-tab-content').forEach(content => content.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    if (tabName === 'users') {
        loadUsers();
    } else if (tabName === 'system') {
        loadSystemStats();
    }
}

async function loadUsers() {
    try {
        const users = await apiCall('/users');
        const tbody = document.getElementById('users-table-body');
        tbody.innerHTML = '';
        
        users.forEach(user => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.is_admin ? 'Yes' : 'No'}</td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
                <td>-</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

async function loadSystemStats() {
    try {
        const users = await apiCall('/users');
        const machines = await apiCall('/machines');
        const routes = await apiCall('/routes');
        
        document.getElementById('total-users').textContent = users.length;
        document.getElementById('total-machines').textContent = machines.length;
        document.getElementById('total-routes').textContent = routes.length;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function showCreateUserModal() {
    document.getElementById('create-user-modal').classList.add('active');
}

function closeCreateUserModal() {
    document.getElementById('create-user-modal').classList.remove('active');
    document.getElementById('create-user-form').reset();
}

async function createUser(event) {
    event.preventDefault();
    
    const username = document.getElementById('user-username').value;
    const password = document.getElementById('user-password').value;
    const isAdmin = document.getElementById('user-admin').checked;
    
    try {
        await apiCall('/users', {
            method: 'POST',
            body: JSON.stringify({ username, password, is_admin: isAdmin })
        });
        
        closeCreateUserModal();
        await loadUsers();
        showAlert('User created successfully', 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

// Password Change Functions
function showChangePasswordModal() {
    document.getElementById('change-password-modal').classList.add('active');
}

function closeChangePasswordModal() {
    document.getElementById('change-password-modal').classList.remove('active');
    document.getElementById('change-password-form').reset();
}

async function changePassword(event) {
    event.preventDefault();
    
    const oldPassword = document.getElementById('old-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    if (newPassword !== confirmPassword) {
        showAlert('New passwords do not match');
        return;
    }
    
    if (newPassword.length < 4) {
        showAlert('Password must be at least 4 characters');
        return;
    }
    
    try {
        // Get current user ID
        const user = await apiCall('/user/me');
        
        await apiCall(`/users/${user.id}/password`, {
            method: 'PUT',
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword
            })
        });
        
        closeChangePasswordModal();
        showAlert('Password changed successfully', 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

// API Key Management
async function deleteAPIKey(keyId) {
    if (!confirm('Are you sure you want to invalidate this API key? Any machines using it will be disconnected.')) {
        return;
    }
    
    try {
        await apiCall(`/api_keys/${keyId}`, {
            method: 'DELETE'
        });
        await loadAPIKeys();
        showAlert('API key invalidated', 'success');
    } catch (error) {
        showAlert(error.message);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    if (path === '/dashboard' || path === '/') {
        loadDashboard();
    } else if (path === '/admin') {
        loadUsers();
        loadSystemStats();
    }
});

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.classList.remove('active');
        }
    });
};

