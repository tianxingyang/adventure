# Adventure Game Framework

A web-based framework for creating and playing interactive text adventure games with a visual node editor.

## Features

- **Visual Node Editor**: Create branching storylines with drag-and-drop interface
- **Conditional Logic**: Set conditions on choices based on game state
- **Game State Management**: Track player progress and decisions
- **Export Functionality**: Generate standalone web games
- **Rich Content**: Add formatted text and multimedia to game nodes
- **Project Management**: Save, load, and organize multiple game projects

## Technology Stack

- **Backend**: Python FastAPI with PostgreSQL
- **Frontend**: React with React Flow for visual editing
- **State Management**: Zustand for React state
- **Database**: SQLAlchemy ORM with PostgreSQL

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL 13+

### Backend Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd adventure-game-framework
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Run the development server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Project Structure

```
adventure-game-framework/
├── adventure_game/          # Main application package
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   ├── api/                 # API layer
│   │   └── routes/          # API endpoints
│   └── config/              # Configuration
├── tests/                   # Test files
├── templates/               # HTML templates for exports
├── main.py                  # FastAPI application entry point
└── requirements.txt         # Python dependencies
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
flake8 .
```

### Database Migrations

```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## License

MIT License - see LICENSE file for details.