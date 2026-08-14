# PlaneTracker

<img width="1248" height="741" alt="image" src="https://github.com/user-attachments/assets/225447d5-176d-4029-a8eb-20e1c9639ccc" />

A real-time aircraft tracking application that displays live flight data on an interactive 3D globe. PlaneTracker integrates multiple aviation data providers and features a database to keep fetched data for favorited aircrafts.

## Features

- **Real-time Aircraft Tracking**: Live position updates with multiple provider support and automatic fallback
- **Interactive 3D Globe**: Globe.gl-powered visualization
- **Search & Discovery**: Query aircraft by hex code, call sign, or registration (depends on a provider's API)
- **Favorites Management**: Save and monitor specific aircrafts with persistent storage
- **Flight History**: Track aircraft position history over time

## Architecture

### Backend Stack
- **Framework**: FastAPI with uvicorn server
- **Database**: SQLite with SQLAlchemy ORM
- **Data Providers**: Pluggable provider interface with built-in examples
- **Communication**: Real-time client updates, REST API for search/favorites

### Frontend Stack
- **Visualization**: Globe.gl (Three.js-based 3D globe)
- **Communication**: Client with automatic reconnection
- **Build**: Vanilla JavaScript (no build step required for basic use)

## Project Structure

```
PlaneTracker/
├── api/                           # Data provider interface
│   ├── aircraft_information_interface.py
│   └── providers/
│       ├── base.py
│       ├── airplaneslive/
│       └── opensky/
├── db/                            # Database layer
│   ├── models.py
│   ├── database.py
│   ├── upserts.py
│   └── diagnose_history.py
├── gui/                           # Frontend & server
│   ├── index.html
│   ├── main.js
│   ├── package.json
│   └── server/
│       ├── main.py
│       ├── aircraft_service.py
│       ├── background_tasks.py
│       └── routes/
├── container.py
├── exceptions.py
├── pyproject.toml
└── main.py
```

## Installation

1. **Clone and enter the repository**:
   ```bash
   cd \PlaneTracker
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

### Accessing the Application

- run 'npm install' and 'npm start' in the gui folder to start the app

## Configuration

Available providers:
- **Planes Live**: Real-time ADS-B data (rate limited, high block probability)
- **OpenSky Network**: Community aircraft database (registration required)

### Database

Default: SQLite at `aircraft.db` (created automatically)

The database includes:
- `aircraft` - Aircraft metadata (registration, type)
- `aircraft_state` - Current position and telemetry
- `position_history` - (Optional) Historical position log
- `favorite` - User favorites

### Adding a Custom Provider

Create a custom provider in `api/providers/`:

```python
from .base import BaseProvider, AircraftInformationBaseResponse


class MyProvider(BaseProvider):
    async def fetch_data(self, search: list[str], api_endpoint: str | None):
        # Fetch raw data from your source
        pass

    def normalize_response(self, raw_data) -> list[AircraftInformationBaseResponse]:
        # Convert to standard response format
        pass
```

Register in `container.py`.

## Dependencies

See `pyproject.toml`:
