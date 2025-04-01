from flask import Blueprint, render_template, request, jsonify, session, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd
import re  # Добавляем импорт re для регулярных выражений
from utils.excel_analyzer import analyze_excel_files, save_results_to_csv
from database.db import get_session, get_student_by_name, add_student, get_subject_by_name, create_notification, get_unique_classes_sorted, get_students_by_class_sorted  # Добавляем импорт get_students_by_class_sorted
import uuid

analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')

# Убедимся, что папки для временных файлов существуют
os.makedirs('uploads/excel_files', exist_ok=True)
os.makedirs('temp', exist_ok=True)

@analysis_bp.route('/')
def index():
    """Main page of analysis module"""
    # Get list of classes
    classes = get_unique_classes_sorted()
    
    # Get available analysis sessions by class
    db_session = get_session()
    analysis_sessions = db_session.query(AnalysisSession).order_by(
        AnalysisSession.class_name, 
        AnalysisSession.latest_date.desc()
    ).all()
    
    # Group sessions by class
    sessions_by_class = {}
    for session in analysis_sessions:
        if session.class_name not in sessions_by_class:
            sessions_by_class[session.class_name] = []
        sessions_by_class[session.class_name].append({
            'id': session.id,
            'earliest_date': session.earliest_date.strftime('%d.%m.%Y') if session.earliest_date else 'Unknown',
            'latest_date': session.latest_date.strftime('%d.%m.%Y') if session.latest_date else 'Unknown',
            'created_at': session.created_at.strftime('%d.%m.%Y %H:%M')
        })
    
    db_session.close()
    
    return render_template('analysis/index.html', 
                           classes=classes,
                           sessions_by_class=sessions_by_class)
@analysis_bp.route('/session/<int:session_id>')
def view_session(session_id):
    """View existing analysis session"""
    db_session = get_session()
    analysis_session = db_session.query(AnalysisSession).get(session_id)
    
    if not analysis_session:
        flash('Analysis session not found', 'danger')
        return redirect(url_for('analysis.index'))
    
    # Set session variables for compatibility with existing code
    session['analysis_session_id'] = str(analysis_session.id)
    session['analysis_class_name'] = analysis_session.class_name
    
    # Rerun analysis or load cached results
    results = analyze_excel_files(analysis_session.folder_path, analysis_session.class_name)
    session['analysis_results'] = json.dumps(results)
    
    db_session.close()
    
    return redirect(url_for('analysis.analyze', session_id=str(analysis_session.id)))

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
    
    # Сохраняем все файлы с уникальными именами
    file_paths = []
    print(f"Загрузка {len(files)} файлов в папку {folder_path}")
    
    for index, file in enumerate(files, 1):
        if file.filename == '':
            continue
        
        # Получаем безопасное имя файла
        original_filename = secure_filename(file.filename)
        
        # Добавляем уникальный идентификатор к имени файла
        file_uuid = uuid.uuid4().hex[:8]  # 8 символов будет достаточно
        base, ext = os.path.splitext(original_filename)
        unique_filename = f"{base}_{file_uuid}{ext}"
        
        file_path = os.path.join(folder_path, unique_filename)
        file.save(file_path)
        file_paths.append(file_path)
        
        print(f"Сохранение файла {index}/{len(files)}: {original_filename} → {unique_filename}")
    
    if not file_paths:
        return jsonify({'success': False, 'message': 'Не загружено ни одного файла'})
    
    # Сохраняем класс в сессии для дальнейшего использования
    session['analysis_class_name'] = class_name
    
    # Выполняем анализ сразу здесь для ускорения процесса
    results = analyze_excel_files(folder_path, class_name)
    earliest_date, latest_date = extract_file_dates(folder_path)
    
    # Store analysis session in database
    session_db = get_session()
    analysis_session = AnalysisSession(
        class_name=class_name,
        folder_path=folder_path,
        earliest_date=earliest_date,
        latest_date=latest_date
    )
    session_db.add(analysis_session)
    session_db.commit()
    session_db.close()
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
    failed_subjects_details = []
    satisfactory_subjects_details = []
    
    for result in student_results:
        subject_name = result['Предмет']
        problem_type = result['Тип проблемы']
        period = result['Период промежуточной аттестации']
        
        subject_detail = {
            'name': subject_name,
            'period': period
        }
        
        if 'Задолженность' in problem_type:
            failed_subjects_details.append(subject_detail)
        elif problem_type == 'Тройка':
            satisfactory_subjects_details.append(subject_detail)
    
    # Convert to URL-friendly format
    import json
    failed_subjects_json = json.dumps(failed_subjects_details)
    satisfactory_subjects_json = json.dumps(satisfactory_subjects_details)
    
    return jsonify({
        'success': True,
        'student_id': student_id,
        'student_name': student_name,
        'student_class': student_class,
        'failed_subjects': failed_subjects,
        'satisfactory_subjects': satisfactory_subjects,
        'failed_subjects_details': failed_subjects_details,
        'satisfactory_subjects_details': satisfactory_subjects_details,
        'failed_subjects_json': failed_subjects_json,
        'satisfactory_subjects_json': satisfactory_subjects_json
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