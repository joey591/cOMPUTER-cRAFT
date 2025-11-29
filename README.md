# ComputerCraft + Create Mod Item Transporter

A Flask web application that manages item transport routes between ComputerCraft machines and Create mod peripherals. Features a sleek web interface for route management and automatic item transportation.

## Features

- **Web Interface**: Modern, dark-themed UI for managing routes and monitoring machines
- **User Authentication**: Session-based login with admin/user roles
- **API Key System**: Per-user API keys for connecting ComputerCraft machines
- **Fuzzy Item Filtering**: Smart item matching (e.g., `iron_b` → `iron_block`, `iron_i` → `iron_ingot`)
- **Automatic Peripheral Discovery**: Background job discovers and updates peripherals
- **Route Management**: Create, edit, and manage item transport routes
- **Real-time Status**: Monitor machine and peripheral status

## Requirements

- Python 3.8+
- Flask 3.0.0+
- ComputerCraft mod (Minecraft 1.20.1)
- Create mod (Minecraft 1.20.1)

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the Flask application:
```bash
python run.py
```

The server will start on `http://localhost:5000` by default.

## Default Login

- **Username**: `admin`
- **Password**: `admin`

**Important**: Change the default password after first login!

## ComputerCraft Setup

### Option 1: Using the Installation Script

1. In your ComputerCraft computer, run:
```lua
wget http://your-server:5000/static/install.lua install
install
```

2. Follow the prompts to enter your API key and machine name

### Option 2: Manual Setup

1. Copy `computercraft/transporter.lua` to your ComputerCraft computer

2. Create a configuration file `transporter_config`:
```lua
{
    server_url = "http://your-server:5000",
    api_key = "your-api-key-here",
    machine_name = "My Computer",
    poll_interval = 5,
    retry_delay = 2,
    max_retries = 3
}
```

3. Run the transporter:
```lua
transporter
```

## Getting an API Key

1. Log in to the web interface
2. Go to the Dashboard
3. Click "Generate API Key"
4. Copy the key (it will only be shown once!)
5. Use this key when setting up your ComputerCraft machines

## Usage

### Creating Routes

1. Log in to the web dashboard
2. Ensure your ComputerCraft machines are connected and peripherals are discovered
3. Click "Create Route"
4. Select source and destination peripherals
5. Optionally specify item filters:
   - Type item names (e.g., `iron_ingot`)
   - Use abbreviations (e.g., `iron_i` for `iron_ingot`, `iron_b` for `iron_block`)
   - The system will suggest matching items as you type
6. Click "Create Route"

### Managing Routes

- **Enable/Disable**: Toggle routes on or off
- **Delete**: Remove routes you no longer need
- Routes are automatically executed by connected ComputerCraft machines

### Admin Features

Admins can:
- Create and manage users
- View system statistics
- Monitor all machines and routes

## Configuration

Edit `backend/config.py` to customize:

- `DATABASE_PATH`: SQLite database location
- `SECRET_KEY`: Flask secret key (change in production!)
- `PERIPHERAL_DISCOVERY_INTERVAL`: How often to discover peripherals (seconds)
- `MACHINE_TIMEOUT`: Time before marking machine as offline (seconds)
- `SERVER_HOST` and `SERVER_PORT`: Server binding

## Project Structure

```
cOMPUTER-cRAFT/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── models.py              # Database models
│   ├── auth.py                # Authentication utilities
│   ├── routes.py              # API and web routes
│   ├── peripheral_discovery.py # Background discovery job
│   ├── item_filter.py         # Fuzzy item matching
│   └── config.py              # Configuration
├── frontend/
│   ├── static/
│   │   ├── css/style.css      # Styling
│   │   └── js/app.js          # Frontend JavaScript
│   └── templates/             # HTML templates
├── computercraft/
│   ├── transporter.lua        # Main CC script
│   └── install.lua            # Installation script
├── requirements.txt
├── run.py
└── README.md
```

## API Endpoints

### Web Interface
- `GET /` - Redirect to login or dashboard
- `GET/POST /login` - Login page
- `GET /dashboard` - User dashboard
- `GET /admin` - Admin dashboard

### Web API
- `GET /api/api_keys` - List API keys
- `POST /api/api_keys` - Generate API key
- `GET /api/machines` - List machines
- `GET /api/peripherals` - List peripherals
- `POST /api/items/search` - Search items with fuzzy matching
- `GET /api/routes` - List routes
- `POST /api/routes` - Create route
- `PUT /api/routes/<id>` - Update route
- `DELETE /api/routes/<id>` - Delete route

### ComputerCraft API
- `POST /api/auth` - Authenticate machine (requires API key)
- `POST /api/peripherals` - Register peripherals
- `GET /api/routes` - Get routes for machine
- `GET /api/commands` - Poll for transport commands
- `POST /api/status` - Update machine status

## Item Filtering

The system supports intelligent item name matching:

- **Exact match**: `iron_ingot` matches `iron_ingot`
- **Abbreviation**: `iron_i` → `iron_ingot`, `iron_b` → `iron_block`
- **Prefix match**: `iron` matches `iron_ingot`, `iron_block`, etc.
- **Fuzzy match**: Similar item names are matched automatically

## Troubleshooting

### ComputerCraft machine not connecting
- Verify the API key is correct
- Check that the server URL is accessible from the computer
- Ensure HTTP API is enabled in ComputerCraft config

### Peripherals not discovered
- Make sure peripherals are properly connected to the computer
- Check that the computer has reported its peripherals to the server
- Verify peripheral names match between CC and the web interface

### Items not transferring
- Check that both source and destination peripherals support item transfer
- Verify the route is enabled
- Ensure item filters match the actual item names
- Check ComputerCraft computer logs for errors

## License

This project is provided as-is for use with ComputerCraft and Create mod.

## Contributing

Feel free to submit issues or pull requests for improvements!

