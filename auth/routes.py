from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from .models import User
from database.db import get_session

auth_bp = Blueprint('auth', __name__)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    session = get_session()
    user = session.query(User).get(int(user_id))
    session.close()
    return user

def init_auth(app):
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    
    # Создание начального администратора, если его нет
    with app.app_context():
        session = get_session()
        admin = session.query(User).filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True)
            admin.set_password('password')  # Пароль для первичного входа
            session.add(admin)
            session.commit()
        session.close()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем его
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('create_notification'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        session = get_session()
        user = session.query(User).filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            session.close()
            
            # Перенаправление после входа
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                if user.is_admin:
                    # Перенаправляем админа на панель управления
                    next_page = url_for('admin.dashboard')
                else:
                    # Обычных пользователей - на страницу создания уведомлений
                    next_page = url_for('create_notification')
            
            return redirect(next_page)
        
        session.close()
        flash('Неверное имя пользователя или пароль', 'danger')
    
    # Важно! Только рендерим страницу входа, без других шаблонов
    return render_template('auth/login.html')
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'success')
    return redirect(url_for('auth.login'))

# Функция для проверки прав администратора
def admin_required(func):
    @login_required
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin:
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    decorated_view.__name__ = func.__name__
    return decorated_view

@admin_bp.route('/')
@admin_required@admin_required
def dashboard():
    """Административная панель"""
    # Важно! Рендерим только шаблон dashboard, без других шаблонов
    return render_template('admin/dashboard.html')