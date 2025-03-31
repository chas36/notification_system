import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from auth.models import User
from database.db import get_session, get_student_by_id, add_student, get_unique_classes_sorted
from database.models import Subject, ClassProfile, Student
from auth.routes import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def init_admin(app):
    app.register_blueprint(admin_bp)

@admin_bp.route('/')
@admin_required
def dashboard():
    """Административная панель"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/students')
@admin_required
def students():
    """Страница управления учениками"""
    session = get_session()
    students = session.query(Student).all()  # Запрашиваем правильную модель Student
    session.close()
    return render_template('admin/students.html', students=students)

@admin_bp.route('/subjects')
@admin_required
def subjects():
    """Страница управления предметами"""
    session = get_session()
    subjects = session.query(Subject).all()
    session.close()
    return render_template('admin/subjects.html', subjects=subjects)

@admin_bp.route('/class_profiles')
@admin_required
def class_profiles():
    """Страница управления профильными предметами по классам"""
    session = get_session()
    # Получаем список всех классов
    classes = get_unique_classes_sorted()
    profiles = session.query(ClassProfile).all()
    subjects = session.query(Subject).all()
    session.close()
    
    # Создаем словарь профилей для JavaScript
    profiles_by_class = {}
    for profile in profiles:
        if profile.class_name not in profiles_by_class:
            profiles_by_class[profile.class_name] = []
        profiles_by_class[profile.class_name].append(profile.subject_id)
    
    return render_template('admin/class_profiles.html', 
                          profiles=profiles_by_class, 
                          subjects=subjects, 
                          classes=classes)

@admin_bp.route('/update_class_profile', methods=['POST'])
@admin_required
def update_class_profile():
    """Обновление профиля класса (связь класса и профильных предметов)"""
    class_name = request.form.get('class_name')
    subject_ids = request.form.getlist('subject_ids[]')
    
    if not class_name:
        return jsonify({'success': False, 'message': 'Не указано название класса'})
    
    session = get_session()
    
    try:
        # Удаляем старые профили для этого класса
        session.query(ClassProfile).filter_by(class_name=class_name).delete()
        
        # Добавляем новые профили
        for subject_id in subject_ids:
            profile = ClassProfile(class_name=class_name, subject_id=int(subject_id))
            session.add(profile)
        
        session.commit()
        return jsonify({'success': True, 'message': 'Профильные предметы успешно обновлены'})
    
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка при обновлении профиля: {str(e)}'})
    
    finally:
        session.close()

@admin_bp.route('/add_student', methods=['POST'])
@admin_required
def add_student():
    """Добавление нового ученика"""
    full_name = request.form.get('full_name')
    class_name = request.form.get('class_name')
    
    if not full_name or not class_name:
        return jsonify({'success': False, 'message': 'Заполните все обязательные поля'})
    
    try:
        student_id = add_student(full_name, class_name)
        return jsonify({'success': True, 'message': 'Ученик успешно добавлен', 'id': student_id})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка при добавлении ученика: {str(e)}'})

@admin_bp.route('/import_from_excel', methods=['POST'])
@admin_required
def import_from_excel():
    """Импорт списка учеников из Excel-файла"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'message': 'Выберите файл Excel (.xlsx или .xls)'})
    
    # Сохраняем файл во временную директорию
    temp_dir = 'temp'
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, secure_filename(file.filename))
    file.save(file_path)
    
    # Импортируем учеников из файла
    from utils.import_export import import_students_from_excel
    result = import_students_from_excel(file_path)
    
    # Удаляем временный файл
    try:
        os.remove(file_path)
    except:
        pass
    
    return jsonify(result)

@admin_bp.route('/get_student/<int:student_id>')
@admin_required
def get_student(student_id):
    """Получение данных ученика по ID"""
    student = get_student_by_id(student_id)
    
    if not student:
        return jsonify({'success': False, 'message': 'Ученик не найден'})
    
    return jsonify({
        'success': True, 
        'student': {
            'id': student.id,
            'full_name': student.full_name,
            'class_name': student.class_name
        }
    })

@admin_bp.route('/update_student', methods=['POST'])
@admin_required
def update_student():
    """Обновление данных ученика"""
    student_id = request.form.get('student_id')
    full_name = request.form.get('full_name')
    class_name = request.form.get('class_name')
    
    if not student_id or not full_name or not class_name:
        return jsonify({'success': False, 'message': 'Заполните все обязательные поля'})
    
    session = get_session()
    student = session.query(Student).filter_by(id=student_id).first()
    
    if not student:
        session.close()
        return jsonify({'success': False, 'message': 'Ученик не найден'})
    
    try:
        student.full_name = full_name
        student.class_name = class_name
        session.commit()
        return jsonify({'success': True, 'message': 'Данные ученика успешно обновлены'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка при обновлении данных: {str(e)}'})
    finally:
        session.close()

@admin_bp.route('/delete_student/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    """Удаление ученика"""
    session = get_session()
    student = session.query(Student).filter_by(id=student_id).first()
    
    if not student:
        session.close()
        return jsonify({'success': False, 'message': 'Ученик не найден'})
    
    try:
        session.delete(student)
        session.commit()
        return jsonify({'success': True, 'message': 'Ученик успешно удален'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка при удалении ученика: {str(e)}'})
    finally:
        session.close()


@admin_bp.route('/delete_all_students', methods=['POST'])
@admin_required
def delete_all_students():
    """Удаление всех учеников"""
    session = get_session()
    
    try:
        # Удаляем все уведомления и связанные с ними записи
        from database.models import Notification, NotificationSubject, NotificationMeta, NotificationConsultation
        
        # Удаляем связанные записи консультаций
        session.query(NotificationConsultation).delete()
        
        # Удаляем связанные записи метаданных
        session.query(NotificationMeta).delete()
        
        # Удаляем связанные записи предметов уведомлений
        session.query(NotificationSubject).delete()
        
        # Удаляем уведомления
        session.query(Notification).delete()
        
        # Удаляем учеников
        session.query(Student).delete()
        
        session.commit()
        return jsonify({'success': True, 'message': 'Все ученики успешно удалены'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': f'Ошибка при удалении учеников: {str(e)}'})
    finally:
        session.close()