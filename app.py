# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session, flash
from werkzeug.utils import secure_filename
import os
from database.db import init_db
from flask_session import Session
from flask_login import current_user, login_required
from config import get_config

def create_app(config_class=None):
    """Factory pattern для создания приложения"""
    app = Flask(__name__)
    
    # Загрузка конфигурации
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Создаем необходимые директории
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['GENERATED_DOCUMENTS_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # Инициализируем сессии
    Session(app)
    
    # Инициализируем базу данных
    init_db()
    
    # Инициализируем аутентификацию
    from auth.routes import init_auth
    init_auth(app)
    
    # Инициализируем административную часть
    from admin.routes import init_admin
    init_admin(app)
    
    # Инициализируем модуль анализа
    from analysis.routes import init_analysis
    init_analysis(app)
    
    # Регистрируем маршруты
    register_routes(app)
    
    return app

def register_routes(app):
    """Register the routes for the main application"""
    
    @app.route('/')
    def index():
        """Главная страница - для всех пользователей направляет на страницу создания уведомления"""
        return redirect(url_for('create_notification'))

    @app.route('/create_notification')
    def create_notification():
        """Страница создания уведомления"""
        from database.db import get_all_template_types
        template_types = get_all_template_types()
        
        return render_template('create_notification.html', 
                            template_types=template_types)

    @app.route('/submit_notification', methods=['POST'])
    def submit_notification():
        """Обработка формы создания уведомления"""
        try:
            # Получаем основные данные
            student_id = request.form.get('student_id')
            template_type_id = request.form.get('template_type_id')
            period = request.form.get('period')
            
            # Проверяем обязательные поля
            if not student_id or not template_type_id or not period:
                return jsonify({'success': False, 'message': 'Заполните все обязательные поля'})
            
            # Получаем данные о выбранных предметах
            failed_subjects = request.form.getlist('failed_subjects[]')
            satisfactory_subjects = request.form.getlist('satisfactory_subjects[]')
            
            if not failed_subjects and not satisfactory_subjects:
                return jsonify({'success': False, 'message': 'Выберите хотя бы один предмет'})
            
            # Получаем ID предметов
            from database.db import get_subject_by_name
            failed_subject_ids = [get_subject_by_name(subject) for subject in failed_subjects]
            satisfactory_subject_ids = [get_subject_by_name(subject) for subject in satisfactory_subjects]
            
            # Все предметы для уведомления
            all_subject_ids = failed_subject_ids + satisfactory_subject_ids
            
            # Создаем сессию
            from database.db import get_session
            session = get_session()
            
            try:
                # Создаем запись уведомления в БД
                from database.db import create_notification
                notification_id = create_notification(
                    student_id=student_id,
                    template_type_id=template_type_id,
                    period=period,
                    subjects_ids=all_subject_ids
                )
                
                # Сохраняем дополнительные данные для генерации документа
                from database.models import NotificationMeta, NotificationConsultation
                
                # Сохраняем информацию о разделении предметов
                meta = NotificationMeta(
                    notification_id=notification_id,
                    key='failed_subjects',
                    value=','.join(failed_subjects)
                )
                session.add(meta)
                
                if satisfactory_subjects:
                    meta = NotificationMeta(
                        notification_id=notification_id,
                        key='satisfactory_subjects',
                        value=','.join(satisfactory_subjects)
                    )
                    session.add(meta)
                
                # Сохраняем дату дедлайна, если указана
                need_deadline = request.form.get('need_deadline') == 'on'
                deadline_date = request.form.get('deadline_date')
                if need_deadline and deadline_date:
                    meta = NotificationMeta(
                        notification_id=notification_id,
                        key='deadline_date',
                        value=deadline_date
                    )
                    session.add(meta)
                
                # Проверяем, нужно ли добавлять график консультаций
                need_consultations = request.form.get('need_consultations') == 'on'
                
                if need_consultations:
                    # Обрабатываем консультации для предметов с задолженностями
                    for subject in failed_subjects:
                        subject_key = subject.replace(' ', '_')
                        
                        # Получаем количество тем для каждого предмета
                        topics_count_key = f'failed_topics_count_{subject_key}'
                        topics_count = int(request.form.get(topics_count_key, 1))
                        
                        for i in range(1, topics_count + 1):
                            prefix = f'failed_consultations_{subject_key}_topic_{i}'
                            
                            # Получаем данные консультации
                            topic_name = request.form.get(f'{prefix}_name', '')
                            date = request.form.get(f'{prefix}_date', '')
                            lesson_id = request.form.get(f'{prefix}_lesson', '')
                            
                            if date and lesson_id:
                                # Получаем время урока
                                from database.db import get_schedule_times
                                schedule_times = get_schedule_times()
                                lesson_info = next((t for t in schedule_times if str(t['id']) == lesson_id), None)
                                
                                if lesson_info:
                                    time = lesson_info['start']
                                    
                                    # Сохраняем консультацию
                                    subject_id = get_subject_by_name(subject)
                                    consultation = NotificationConsultation(
                                        notification_id=notification_id,
                                        subject_id=subject_id,
                                        topic_name=topic_name,
                                        date=date,
                                        time=time,
                                        topic_type='failed'
                                    )
                                    session.add(consultation)
                
                # Сохраняем все изменения
                session.commit()
                
                # Генерируем документ
                from utils.document_generator import generate_document
                result = generate_document(notification_id)
                
                if result['success']:
                    return jsonify({
                        'success': True, 
                        'message': 'Уведомление успешно создано', 
                        'file_path': result['file_path'],
                        'file_name': result['file_name']
                    })
                else:
                    # Если что-то пошло не так с генерацией документа, откатываем транзакцию
                    session.rollback()
                    return jsonify({
                        'success': False, 
                        'message': f'Ошибка при создании документа: {result["message"]}'
                    })
                    
            except Exception as e:
                # В случае ошибки откатываем транзакцию
                session.rollback()
                raise e
            finally:
                # Закрываем сессию
                session.close()
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False, 
                'message': f'Ошибка при создании уведомления: {str(e)}'
            })

    @app.route('/download_document/<path:filename>')
    def download_document(filename):
        """Скачивание сгенерированного документа"""
        return send_file(os.path.join(app.config['GENERATED_DOCUMENTS_FOLDER'], filename), as_attachment=True)

    @app.route('/api/get_students')
    def api_get_students():
        """API для получения списка учеников"""
        from database.db import get_all_students
        students = get_all_students()
        result = [{'id': s.id, 'full_name': s.full_name, 'class_name': s.class_name} for s in students]
        return jsonify(result)

    @app.route('/api/get_unique_classes')
    def api_get_unique_classes():
        """API для получения списка всех классов"""
        from database.db import get_unique_classes_sorted
        unique_classes = get_unique_classes_sorted()
        return jsonify(unique_classes)

    @app.route('/api/get_students_by_class/<class_name>')
    def api_get_students_by_class(class_name):
        """API для получения списка учеников определенного класса"""
        from database.db import get_students_by_class_sorted
        students = get_students_by_class_sorted(class_name)
        result = [{'id': s.id, 'full_name': s.full_name, 'class_name': s.class_name} for s in students]
        return jsonify(result)

    @app.route('/api/get_schedule_times')
    def api_get_schedule_times():
        """API для получения расписания звонков"""
        from database.db import get_schedule_times
        schedule_times = get_schedule_times()
        return jsonify(schedule_times)

    @app.route('/api/get_subjects_by_grade/<grade>')
    def api_get_subjects_by_grade(grade):
        """API для получения предметов по классу"""
        from database.db import get_subjects_by_grade
        subjects_by_grade = get_subjects_by_grade()
        if grade in subjects_by_grade:
            return jsonify(subjects_by_grade[grade])
        return jsonify([])

    @app.route('/students')
    @login_required
    def students_route():
        """Страница управления учениками доступна только авторизованным пользователям"""
        if current_user.is_admin:
            return redirect(url_for('admin.students'))
        else:
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('create_notification'))

    @app.route('/import_debts')
    @login_required
    def import_debts_route():
        """Страница импорта задолженностей доступна только авторизованным пользователям"""
        if current_user.is_admin:
            from database.db import get_all_template_types
            template_types = get_all_template_types()
            return render_template('import_debts.html', template_types=template_types)
        else:
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('create_notification'))

# Создаем экземпляр приложения
app = create_app()

# Запускаем приложение, если файл выполняется напрямую
if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'], port=5001)