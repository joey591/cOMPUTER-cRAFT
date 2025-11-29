#!/usr/bin/env python3
"""Entry point for the Flask application."""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

from app import app

if __name__ == '__main__':
    from config import SERVER_HOST, SERVER_PORT, DEBUG, SSL_ENABLED, SSL_CERT_PATH, SSL_KEY_PATH
    from pathlib import Path
    import os
    
    # Try to auto-detect AMP certificate locations if not specified
    cert_path = None
    key_path = None
    
    if SSL_ENABLED:
        # If paths are provided, use them
        if SSL_CERT_PATH and SSL_KEY_PATH:
            cert_path = Path(SSL_CERT_PATH)
            key_path = Path(SSL_KEY_PATH)
        else:
            # Try common AMP certificate locations
            possible_cert_locations = [
                # AMP common locations (Windows)
                Path(os.getenv('LOCALAPPDATA', '')) / 'AMP' / 'certificates' / 'cert.pem',
                Path(os.getenv('PROGRAMDATA', '')) / 'AMP' / 'certificates' / 'cert.pem',
                # AMP common locations (Linux)
                Path('/opt/amp/certificates/cert.pem'),
                Path('/var/lib/amp/certificates/cert.pem'),
                Path.home() / '.amp' / 'certificates' / 'cert.pem',
                # Common certificate locations
                Path('/etc/ssl/certs/cert.pem'),
                Path('/etc/ssl/certs/server.crt'),
            ]
            
            possible_key_locations = [
                # AMP common locations (Windows)
                Path(os.getenv('LOCALAPPDATA', '')) / 'AMP' / 'certificates' / 'key.pem',
                Path(os.getenv('PROGRAMDATA', '')) / 'AMP' / 'certificates' / 'key.pem',
                # AMP common locations (Linux)
                Path('/opt/amp/certificates/key.pem'),
                Path('/var/lib/amp/certificates/key.pem'),
                Path.home() / '.amp' / 'certificates' / 'key.pem',
                # Common certificate locations
                Path('/etc/ssl/private/key.pem'),
                Path('/etc/ssl/private/server.key'),
            ]
            
            # Try to find certificate files
            for cert_loc in possible_cert_locations:
                if cert_loc.exists():
                    cert_path = cert_loc
                    print(f"Found certificate at: {cert_path}")
                    break
            
            for key_loc in possible_key_locations:
                if key_loc.exists():
                    key_path = key_loc
                    print(f"Found key at: {key_path}")
                    break
            
            if not cert_path or not key_path:
                print("=" * 60)
                print("SSL enabled but certificate files not found!")
                print("=" * 60)
                print("Please set SSL_CERT_PATH and SSL_KEY_PATH environment variables,")
                print("or place certificate files in one of these locations:")
                print("\nCertificate locations tried:")
                for loc in possible_cert_locations:
                    print(f"  - {loc}")
                print("\nKey locations tried:")
                for loc in possible_key_locations:
                    print(f"  - {loc}")
                print("\nRunning without SSL...")
                print("=" * 60)
                cert_path = None
                key_path = None
    
    if SSL_ENABLED and cert_path and key_path:
        # Verify certificate files exist
        if not cert_path.exists():
            print(f"ERROR: SSL certificate file not found: {cert_path}")
            print("Running without SSL...")
            app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
        elif not key_path.exists():
            print(f"ERROR: SSL key file not found: {key_path}")
            print("Running without SSL...")
            app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)
        else:
            # Run with SSL
            print(f"Starting Flask with SSL on {SERVER_HOST}:{SERVER_PORT}")
            print(f"Certificate: {cert_path}")
            print(f"Key: {key_path}")
            app.run(
                host=SERVER_HOST,
                port=SERVER_PORT,
                debug=DEBUG,
                ssl_context=(str(cert_path), str(key_path))
            )
    else:
        # Run without SSL (for development or if certs not found)
        print(f"Starting Flask without SSL on {SERVER_HOST}:{SERVER_PORT}")
        app.run(host=SERVER_HOST, port=SERVER_PORT, debug=DEBUG)

