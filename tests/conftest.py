import pytest
from app import create_app
from config import config
from database.db import init_db
import os
import tempfile

@pytest.fixture
def app():
    """Create and configure a Flask app for testing"""
    # Создаем временный файл базы данных
    db_fd, db_path = tempfile.mkstemp()
    
    # Создаем тестовую конфигурацию
    test_config = config['testing']
    test_config.DATABASE_URI = f'sqlite:///{db_path}'
    
    app = create_app(test_config)
    
    # Создаем контекст приложения для выполнения тестов
    with app.app_context():
        # Инициализируем тестовую базу данных
        init_db()
        
    yield app
    
    # Удаляем временный файл базы данных
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app"""
    return app.test_cli_runner()