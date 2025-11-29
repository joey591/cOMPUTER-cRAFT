"""Background job for discovering and updating peripherals."""
import threading
import time
from datetime import datetime, timedelta
from models import Database, Machine, Peripheral
from config import PERIPHERAL_DISCOVERY_INTERVAL, MACHINE_TIMEOUT, SERVER_HOST, SERVER_PORT


class PeripheralDiscovery:
    """Background service for discovering peripherals from connected machines."""
    
    def __init__(self, app=None):
        self.app = app
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the discovery service."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the discovery service."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _discovery_loop(self):
        """Main discovery loop."""
        while self.running:
            try:
                self._discover_peripherals()
            except Exception as e:
                print(f"Error in peripheral discovery: {e}")
            time.sleep(PERIPHERAL_DISCOVERY_INTERVAL)
    
    def _discover_peripherals(self):
        """Discover peripherals from all online machines."""
        conn = Database().get_connection()
        cursor = conn.cursor()
        
        # Get all machines that were seen recently
        timeout_threshold = (datetime.utcnow() - timedelta(seconds=MACHINE_TIMEOUT)).isoformat()
        cursor.execute('''
            SELECT * FROM machines 
            WHERE status = 'online' AND last_seen > ?
        ''', (timeout_threshold,))
        machines = cursor.fetchall()
        conn.close()
        
        # Mark machines as offline if they haven't been seen
        current_time = datetime.utcnow()
        for machine in machines:
            last_seen = datetime.fromisoformat(machine['last_seen'])
            if (current_time - last_seen).total_seconds() > MACHINE_TIMEOUT:
                Machine.update_status(machine['id'], 'offline')
        
        # Note: Actual peripheral discovery would require the CC machine to report its peripherals
        # This is handled via the API endpoint when machines register/update their peripherals
        # This background job mainly handles cleanup and status updates


def trigger_discovery_for_machine(machine_id):
    """Manually trigger peripheral discovery for a specific machine.
    
    In a real implementation, this might send a request to the CC machine
    to report its peripherals, or query them directly if possible.
    """
    # This would be called when we want to force a refresh
    # For now, peripherals are reported by the CC machines themselves
    pass

