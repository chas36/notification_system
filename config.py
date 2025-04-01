def get_config():
    """
    Возвращает конфигурацию приложения.
    """
    config = {
        'DATABASE_URL': 'sqlite:///notification_system.db',
        'UPLOAD_FOLDER': 'uploads',
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16 МБ максимальный размер файла
        'SECRET_KEY': 'your-secret-key-here',    # Для Flask-Login и сессий
        'SESSION_TYPE': 'filesystem',
        'SESSION_FILE_DIR': 'flask_session'
    }
    return config