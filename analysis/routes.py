# analysis/routes.py
from flask import Blueprint, render_template, request, jsonify, session, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd
from utils.excel_analyzer import analyze_excel_files, save_results_to_csv
from database.db import get_session, get_student_by_name, add_student, get_subject_by_name, create_notification, get_unique_classes_sorted

analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')

# Убедимся, что папки для временных файлов существуют
os.makedirs('uploads/excel_files', exist_ok=True)
os.makedirs('temp', exist_ok=True)

@analysis_bp.route('/')
def index():
    """Главная страница модуля анализа"""
    # Получаем список классов
    classes = get_unique_classes_sorted()
    return render_template('analysis/index.html', classes=classes)

@analysis_bp.route('/upload', methods=['POST'])
def upload_files():
    """Загрузка Excel-файлов для анализа"""
    if 'files[]' not in request.files:
        return jsonify({'success': False, 'message': 'Не выбраны файлы'})
    
    files = request.files.getlist('files[]')
    class_name = request.form.get('class_name', '')
    
    # Создаем уникальную папку для этой сессии
    import uuid
    session_id = str(uuid.uuid4())
    session['analysis_session_id'] = session_id
    
    folder_path = os.path.join('uploads', 'excel_files', session_id)
    os.makedirs(folder_path, exist_ok=True)
    
    # Сохраняем все файлы
    file_paths = []
    for file in files:
        if file.filename == '':
            continue
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(folder_path, filename)
        file.save(file_path)
        file_paths.append(file_path)
    
    if not file_paths:
        return jsonify({'success': False, 'message': 'Не загружено ни одного файла'})
    
    # Сохраняем класс в сессии для дальнейшего использования
    session['analysis_class_name'] = class_name
    
    # Выполняем анализ сразу здесь для ускорения процесса
    results = analyze_excel_files(folder_path, class_name)
    
    # Сохраняем результаты в сессии
    session['analysis_results'] = json.dumps(results)
    
    return jsonify({
        'success': True, 
        'message': f'Загружено {len(file_paths)} файлов', 
        'session_id': session_id,
        'redirect': url_for('analysis.analyze', session_id=session_id)
    })

@analysis_bp.route('/analyze/<session_id>')
def analyze(session_id):
    """Анализ загруженных файлов"""
    if 'analysis_session_id' not in session or session['analysis_session_id'] != session_id:
        flash('Сессия анализа не найдена или истекла', 'danger')
        return redirect(url_for('analysis.index'))
    
    # Получаем класс из сессии
    class_name = session.get('analysis_class_name', '')
    
    # Путь к папке с файлами
    folder_path = os.path.join('uploads', 'excel_files', session_id)
    
    if not os.path.exists(folder_path):
        flash('Файлы не найдены', 'danger')
        return redirect(url_for('analysis.index'))
    
    # Анализируем файлы или получаем результаты из сессии
    try:
        if 'analysis_results' in session:
            results = json.loads(session['analysis_results'])
        else:
            results = analyze_excel_files(folder_path, class_name)
            session['analysis_results'] = json.dumps(results)
        
        if not results:
            flash('Не найдено проблем с успеваемостью в загруженных файлах', 'info')
            return render_template('analysis/no_results.html')
        
        # Получаем полный список учеников этого класса
        all_students = get_students_by_class_sorted(class_name) if class_name else []
        
        # Группируем результаты по ученикам для удобного отображения
        students = {}
        for item in results:
            student_name = item['ФИО ученика']
            if student_name not in students:
                students[student_name] = {
                    'name': student_name,
                    'class': item.get('Класс', class_name),
                    'problems': []
                }
            
            students[student_name]['problems'].append({
                'subject': item['Предмет'],
                'period': item['Период промежуточной аттестации'],
                'date': item['Дата промежуточной аттестации'],
                'grade': item['Итоговая отметка'],
                'type': item['Тип проблемы']
            })
        
        return render_template('analysis/results.html', 
                              students=students, 
                              all_students=all_students,
                              session_id=session_id)
    
    except Exception as e:
        flash(f'Ошибка при анализе файлов: {str(e)}', 'danger')
        return redirect(url_for('analysis.index'))
    
@analysis_bp.route('/analyze/<session_id>')
def analyze(session_id):
    """Анализ загруженных файлов"""
    if 'analysis_session_id' not in session or session['analysis_session_id'] != session_id:
        flash('Сессия анализа не найдена или истекла', 'danger')
        return redirect(url_for('analysis.index'))
    
    # Получаем класс из сессии
    class_name = session.get('analysis_class_name', '')
    
    # Путь к папке с файлами
    folder_path = os.path.join('uploads', 'excel_files', session_id)
    
    if not os.path.exists(folder_path):
        flash('Файлы не найдены', 'danger')
        return redirect(url_for('analysis.index'))
    
    # Анализируем файлы
    try:
        results = analyze_excel_files(folder_path, class_name)
        
        if not results:
            flash('Не найдено проблем с успеваемостью в загруженных файлах', 'info')
            return render_template('analysis/no_results.html')
        
        # Сохраняем результаты в JSON в сессии
        session['analysis_results'] = json.dumps(results)
        
        # Группируем результаты по ученикам для удобного отображения
        students = {}
        for item in results:
            student_name = item['ФИО ученика']
            if student_name not in students:
                students[student_name] = {
                    'name': student_name,
                    'class': item.get('Класс', class_name),
                    'problems': []
                }
            
            students[student_name]['problems'].append({
                'subject': item['Предмет'],
                'period': item['Период промежуточной аттестации'],
                'date': item['Дата промежуточной аттестации'],
                'grade': item['Итоговая отметка'],
                'type': item['Тип проблемы']
            })
        
        # Получаем список всех учеников данного класса
        all_students = get_students_by_class_sorted(class_name)
        
        return render_template('analysis/results.html', 
                            students=students,
                            all_students=all_students,
                            class_name=class_name,
                            session_id=session_id)
    
    except Exception as e:
        flash(f'Ошибка при анализе файлов: {str(e)}', 'danger')
        return redirect(url_for('analysis.index'))

@analysis_bp.route('/download/<session_id>')
def download_results(session_id):
    """Скачивание результатов анализа в CSV"""
    if 'analysis_session_id' not in session or session['analysis_session_id'] != session_id:
        flash('Сессия анализа не найдена или истекла', 'danger')
        return redirect(url_for('analysis.index'))
    
    if 'analysis_results' not in session:
        flash('Результаты анализа не найдены', 'danger')
        return redirect(url_for('analysis.index'))
    
    # Извлекаем результаты из сессии
    results = json.loads(session['analysis_results'])
    
    # Путь для сохранения CSV
    output_path = os.path.join('temp', f'results_{session_id}.csv')
    
    # Сохраняем в CSV
    save_results_to_csv(results, output_path)
    
    return send_file(output_path, as_attachment=True, download_name='students_with_problems.csv')

@analysis_bp.route('/get_student_data/<student_name>/<session_id>')
def get_student_data(student_name, session_id):
    """Получение данных ученика для предзаполнения формы уведомления"""
    if 'analysis_session_id' not in session or session['analysis_session_id'] != session_id:
        return jsonify({'success': False, 'message': 'Сессия анализа не найдена или истекла'})
    
    if 'analysis_results' not in session:
        return jsonify({'success': False, 'message': 'Результаты анализа не найдены'})
    
    # Получаем данные из сессии
    results = json.loads(session['analysis_results'])
    
    # Фильтруем результаты для указанного ученика
    student_results = [r for r in results if r['ФИО ученика'] == student_name]
    
    if not student_results:
        return jsonify({'success': False, 'message': 'Не найдено результатов для указанного ученика'})
    
    # Получаем класс ученика из результатов
    student_class = student_results[0].get('Класс', '')
    
    # Получаем ученика из базы данных или создаем нового
    db_session = get_session()
    student = get_student_by_name(student_name)
    
    if not student:
        # Если ученика нет, добавляем его
        student_id = add_student(student_name, student_class)
    else:
        student_id = student.id
    
    # Получаем список предметов с задолженностями и тройками
    failed_subjects = []
    satisfactory_subjects = []
    
    for result in student_results:
        subject_name = result['Предмет']
        problem_type = result['Тип проблемы']
        
        if problem_type == 'Задолженность':
            failed_subjects.append(subject_name)
        elif problem_type == 'Тройка':
            satisfactory_subjects.append(subject_name)
    
    db_session.close()
    
    return jsonify({
        'success': True,
        'student_id': student_id,
        'student_name': student_name,
        'student_class': student_class,
        'failed_subjects': failed_subjects,
        'satisfactory_subjects': satisfactory_subjects
    })

@analysis_bp.route('/create_notification/<session_id>', methods=['POST'])
def create_notification_from_analysis(session_id):
    """Создание уведомления на основе результатов анализа"""
    if 'analysis_session_id' not in session or session['analysis_session_id'] != session_id:
        return jsonify({'success': False, 'message': 'Сессия анализа не найдена или истекла'})
    
    if 'analysis_results' not in session:
        return jsonify({'success': False, 'message': 'Результаты анализа не найдены'})
    
    student_name = request.form.get('student_name')
    template_type_id = request.form.get('template_type_id', '1')  # По умолчанию 1
    period = request.form.get('period', '1')  # По умолчанию 1
    
    if not student_name:
        return jsonify({'success': False, 'message': 'Не указано имя ученика'})
    
    # Извлекаем результаты из сессии
    results = json.loads(session['analysis_results'])
    
    # Фильтруем результаты для указанного ученика
    student_results = [r for r in results if r['ФИО ученика'] == student_name]
    
    if not student_results:
        return jsonify({'success': False, 'message': 'Не найдено результатов для указанного ученика'})
    
    # Получаем класс ученика из результатов
    student_class = student_results[0].get('Класс', '')
    
    # Проверяем, есть ли ученик в базе, если нет - добавляем
    db_session = get_session()
    student = get_student_by_name(student_name)
    
    if not student:
        # Если ученика нет, добавляем его
        student_id = add_student(student_name, student_class)
    else:
        student_id = student.id
    
    # Собираем предметы и их типы (задолженность или тройка)
    failed_subjects = []
    satisfactory_subjects = []
    
    for result in student_results:
        subject_name = result['Предмет']
        problem_type = result['Тип проблемы']
        
        if problem_type == 'Задолженность':
            failed_subjects.append(subject_name)
        elif problem_type == 'Тройка':
            satisfactory_subjects.append(subject_name)
    
    # Получаем ID предметов
    failed_subject_ids = [get_subject_by_name(name) for name in failed_subjects]
    satisfactory_subject_ids = [get_subject_by_name(name) for name in satisfactory_subjects]
    
    # Все предметы для уведомления
    all_subject_ids = failed_subject_ids + satisfactory_subject_ids
    
    # Создаем уведомление
    try:
        notification_id = create_notification(
            student_id=student_id,
            template_type_id=template_type_id,
            period=period,
            subjects_ids=all_subject_ids
        )
        
        # Сохраняем дополнительные метаданные для генерации документа
        from database.models import NotificationMeta
        
        # Сохраняем информацию о разделении предметов
        meta = NotificationMeta(
            notification_id=notification_id,
            key='failed_subjects',
            value=','.join(failed_subjects)
        )
        db_session.add(meta)
        
        if satisfactory_subjects:
            meta = NotificationMeta(
                notification_id=notification_id,
                key='satisfactory_subjects',
                value=','.join(satisfactory_subjects)
            )
            db_session.add(meta)
        
        db_session.commit()
        db_session.close()
        
        # Генерируем документ
        from utils.document_generator import generate_document
        result = generate_document(notification_id)
        
        if result['success']:
            return jsonify({
                'success': True, 
                'message': 'Уведомление успешно создано', 
                'file_path': result['file_path'],
                'file_name': result['file_name'],
                'download_url': url_for('download_document', filename=result['file_name'])
            })
        else:
            return jsonify({
                'success': False, 
                'message': f'Ошибка при создании документа: {result["message"]}'
            })
    
    except Exception as e:
        db_session.rollback()
        db_session.close()
        return jsonify({
            'success': False, 
            'message': f'Ошибка при создании уведомления: {str(e)}'
        })

def init_analysis(app):
    app.register_blueprint(analysis_bp)