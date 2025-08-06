"""
Database configuration and connection management.

This module provides database connection setup, session management, and
configuration for the adventure game framework using SQLAlchemy.
"""

import os
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base


class DatabaseConfig:
    """Configuration class for database settings."""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.echo_sql = self._get_echo_setting()
        self.pool_settings = self._get_pool_settings()
    
    def _get_database_url(self) -> str:
        """Get database URL from environment or use default."""
        # Check for explicit database URL
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        
        # Build URL from components
        db_type = os.getenv("DB_TYPE", "postgresql")
        db_user = os.getenv("DB_USER", "adventure_user")
        db_password = os.getenv("DB_PASSWORD", "adventure_pass")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "adventure_game")
        
        if db_type == "sqlite":
            # SQLite for development/testing
            db_path = os.getenv("DB_PATH", "adventure_game.db")
            return f"sqlite:///{db_path}"
        elif db_type == "postgresql":
            # PostgreSQL for production
            return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _get_echo_setting(self) -> bool:
        """Get SQL echo setting from environment."""
        return os.getenv("DB_ECHO", "false").lower() in ("true", "1", "yes")
    
    def _get_pool_settings(self) -> dict:
        """Get connection pool settings."""
        return {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        }


class DatabaseManager:
    """Database connection and session management."""
    
    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self._engine: Engine = None
        self._session_factory: sessionmaker = None
    
    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine instance."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory for creating database sessions."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
        return self._session_factory
    
    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with proper configuration."""
        engine_kwargs = {
            "echo": self.config.echo_sql,
        }
        
        # Add pool settings for non-SQLite databases
        if not self.config.database_url.startswith("sqlite"):
            engine_kwargs.update(self.config.pool_settings)
        else:
            # SQLite-specific settings
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 20
                }
            })
        
        return create_engine(self.config.database_url, **engine_kwargs)
    
    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self) -> None:
        """Drop all database tables. WARNING: This deletes all data!"""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with automatic commit/rollback.
        
        Usage:
            with db_manager.session_scope() as session:
                # Use session here
                session.add(model_instance)
                # Automatic commit on success, rollback on exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.session_scope() as session:
                session.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def close(self) -> None:
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global database manager instance
_db_manager: DatabaseManager = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def initialize_database(config: DatabaseConfig = None, create_tables: bool = True) -> DatabaseManager:
    """
    Initialize the global database manager.
    
    Args:
        config: Database configuration (uses default if None)
        create_tables: Whether to create database tables
        
    Returns:
        Initialized DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(config)
    
    if create_tables:
        _db_manager.create_tables()
    
    return _db_manager


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.
    
    Usage in FastAPI route:
        @app.get("/endpoint")
        def endpoint(session: Session = Depends(get_db_session)):
            # Use session here
    """
    db_manager = get_database_manager()
    with db_manager.session_scope() as session:
        yield session


def close_database():
    """Close the global database manager."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None


# Utility functions for common database operations
def create_development_database() -> DatabaseManager:
    """Create a development database with SQLite."""
    config = DatabaseConfig()
    # Override settings for development
    os.environ["DB_TYPE"] = "sqlite"
    os.environ["DB_PATH"] = "adventure_game_dev.db"
    os.environ["DB_ECHO"] = "true"
    
    config = DatabaseConfig()  # Recreate with new env vars
    return initialize_database(config, create_tables=True)


def create_test_database() -> DatabaseManager:
    """Create an in-memory test database."""
    config = DatabaseConfig()
    # Override for testing
    os.environ["DB_TYPE"] = "sqlite"
    os.environ["DB_PATH"] = ":memory:"
    
    config = DatabaseConfig()  # Recreate with new env vars
    return initialize_database(config, create_tables=True)


def setup_production_database() -> DatabaseManager:
    """Setup production database with environment configuration."""
    # Ensure required environment variables are set
    required_vars = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    return initialize_database(create_tables=False)  # Don't auto-create in production


# Database health check
async def database_health_check() -> dict:
    """
    Perform database health check.
    
    Returns:
        Dictionary with health check results
    """
    db_manager = get_database_manager()
    
    try:
        connection_ok = db_manager.test_connection()
        
        # Get basic statistics
        with db_manager.session_scope() as session:
            from .models import Project, GameNode, Choice, GameState
            
            stats = {
                "projects": session.query(Project).count(),
                "nodes": session.query(GameNode).count(),
                "choices": session.query(Choice).count(),
                "game_states": session.query(GameState).count(),
            }
        
        return {
            "status": "healthy" if connection_ok else "unhealthy",
            "database_url": db_manager.config.database_url.split("@")[-1] if "@" in db_manager.config.database_url else "local",
            "connection": "ok" if connection_ok else "failed",
            "statistics": stats if connection_ok else None,
        }
    
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection": "failed",
        }