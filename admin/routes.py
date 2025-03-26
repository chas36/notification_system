# admin/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from auth.routes import admin_required
from database.db import get_session, get_all_students_sorted, add_student, get_unique_classes_sorted
from database.models import Student, Subject
from werkzeug.utils import secure_filename
import os
from utils.import_export import import_students_from_excel

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def dashboard():
    """Административная панель"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/students')
@admin_required
def students():
    """Управление учениками"""
    all_students = get_all_students_sorted()
    return render_template('admin/students.html', students=all_students)

@admin_bp.route('/add_student', methods=['POST'])
@admin_required
def add_new_student():
    """Добавление нового ученика"""
    full_name = request.form.get('full_name')
    class_name = request.form.get('class_name')
    
    if not full_name or not class_name:
        return jsonify({'success': False, 'message': 'Необходимо указать ФИО и класс'})
    
    student_id = add_student(full_name, class_name)
    return jsonify({'success': True, 'message': 'Ученик успешно добавлен', 'student_id': student_id})

@admin_bp.route('/import_students_excel', methods=['POST'])
@admin_required
def import_from_excel():
    """Импорт учеников из Excel-файла"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        
        # Создаем директорию, если не существует
        os.makedirs('uploads', exist_ok=True)
        
        file.save(file_path)
        
        result = import_students_from_excel(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        return jsonify(result)

@admin_bp.route('/subjects')
@admin_required
def subjects():
    """Управление предметами"""
    session = get_session()
    all_subjects = session.query(Subject).order_by(Subject.name).all()
    session.close()
    
    return render_template('admin/subjects.html', subjects=all_subjects)

@admin_bp.route('/add_subject', methods=['POST'])
@admin_required
def add_subject():
    """Добавление нового предмета"""
    name = request.form.get('name')
    if not name:
        return jsonify({'success': False, 'message': 'Необходимо указать название предмета'})
    
    session = get_session()
    
    # Проверяем существование предмета
    existing = session.query(Subject).filter_by(name=name).first()
    if existing:
        session.close()
        return jsonify({'success': False, 'message': 'Предмет с таким названием уже существует'})
    
    # Добавляем новый предмет
    new_subject = Subject(name=name)
    session.add(new_subject)
    session.commit()
    subject_id = new_subject.id
    session.close()
    
    return jsonify({'success': True, 'message': 'Предмет успешно добавлен', 'subject_id': subject_id})

@admin_bp.route('/class_profiles')
@admin_required
def class_profiles():
    """Управление профильными предметами по классам"""
    classes = get_unique_classes_sorted()
    
    session = get_session()
    all_subjects = session.query(Subject).order_by(Subject.name).all()
    
    # Получаем существующие профильные предметы для классов
    from database.models import ClassProfile
    profiles = {}
    
    class_profiles = session.query(ClassProfile).all()
    for profile in class_profiles:
        if profile.class_name not in profiles:
            profiles[profile.class_name] = []
        
        profiles[profile.class_name].append(profile.subject_id)
    
    session.close()
    
    return render_template('admin/class_profiles.html', 
                          classes=classes, 
                          subjects=all_subjects,
                          profiles=profiles)

@admin_bp.route('/update_class_profile', methods=['POST'])
@admin_required
def update_class_profile():
    """Обновление профильных предметов для класса"""
    class_name = request.form.get('class_name')
    subject_ids = request.form.getlist('subject_ids[]')
    
    if not class_name:
        return jsonify({'success': False, 'message': 'Необходимо указать класс'})
    
    session = get_session()
    
    # Удаляем существующие записи для класса
    from database.models import ClassProfile
    session.query(ClassProfile).filter_by(class_name=class_name).delete()
    
    # Добавляем новые записи
    for subject_id in subject_ids:
        profile = ClassProfile(class_name=class_name, subject_id=int(subject_id))
        session.add(profile)
    
    session.commit()
    session.close()
    
    return jsonify({'success': True, 'message': f'Профильные предметы для класса {class_name} обновлены'})

# Регистрация Blueprint
def init_admin(app):
    app.register_blueprint(admin_bp)