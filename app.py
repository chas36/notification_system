from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import os
from werkzeug.utils import secure_filename
from database.db import init_db, get_all_students, get_all_subjects, get_all_template_types, add_student, create_notification
from utils.import_export import import_students_from_excel, import_students_from_yandex_disk
from utils.document_generator import generate_document

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 МБ максимальный размер файла

# Создаем директории, если они не существуют
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('generated_documents', exist_ok=True)
os.makedirs('temp', exist_ok=True)

# Инициализируем базу данных
init_db()

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/add_student', methods=['POST'])
def add_new_student():
    """Добавление нового ученика"""
    full_name = request.form.get('full_name')
    class_name = request.form.get('class_name')
    
    if not full_name or not class_name:
        return jsonify({'success': False, 'message': 'Необходимо указать ФИО и класс'})
    
    student_id = add_student(full_name, class_name)
    return jsonify({'success': True, 'message': 'Ученик успешно добавлен', 'student_id': student_id})

@app.route('/import_students_excel', methods=['POST'])
def import_from_excel():
    """Импорт учеников из Excel-файла"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        result = import_students_from_excel(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        return jsonify(result)

@app.route('/import_students_yandex', methods=['POST'])
def import_from_yandex():
    """Импорт учеников из таблицы на Яндекс.Диске"""
    api_token = request.form.get('api_token')
    file_path = request.form.get('file_path')
    
    if not api_token or not file_path:
        return jsonify({'success': False, 'message': 'Необходимо указать токен API и путь к файлу'})
    
    result = import_students_from_yandex_disk(api_token, file_path)
    return jsonify(result)

@app.route('/create_notification')
def create_notification_page():
    """Страница создания уведомления"""
    students = get_all_students()
    subjects = get_all_subjects()
    template_types = get_all_template_types()
    
    return render_template('create_notification.html', 
                           students=students, 
                           subjects=subjects, 
                           template_types=template_types)

# Обновленный обработчик запроса для app.py

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
        
        # Получаем информацию о дедлайне
        need_deadline = request.form.get('need_deadline') == 'on'
        deadline_date = request.form.get('deadline_date')
        
        # Создаем запись уведомления в БД
        from database.db import create_notification, get_student_by_id
        notification_id = create_notification(
            student_id=student_id,
            template_type_id=template_type_id,
            period=period,
            subjects_ids=all_subject_ids
        )
        
        # Сохраняем дополнительные данные для генерации документа
        from database.models import NotificationMeta, NotificationConsultation
        from database.db import get_session
        
        session = get_session()
        
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
                                topic_type='failed'  # Тип "задолженность"
                            )
                            session.add(consultation)
            
            # Обрабатываем консультации для предметов с удовлетворительными оценками
            for subject in satisfactory_subjects:
                subject_key = subject.replace(' ', '_')
                topics_count_key = f'satisfactory_topics_count_{subject_key}'
                topics_count = int(request.form.get(topics_count_key, 1))
                
                for i in range(1, topics_count + 1):
                    prefix = f'satisfactory_consultations_{subject_key}_topic_{i}'
                    
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
                                topic_type='satisfactory'  # Тип "удовлетворительно"
                            )
                            session.add(consultation)
        
        # Сохраняем все изменения
        session.commit()
        session.close()
        
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
            return jsonify({
                'success': False, 
                'message': f'Ошибка при создании документа: {result["message"]}'
            })
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
    return send_file(os.path.join('generated_documents', filename), as_attachment=True)

@app.route('/api/get_students')
def api_get_students():
    """API для получения списка учеников"""
    students = get_all_students()
    result = [{'id': s.id, 'full_name': s.full_name, 'class_name': s.class_name} for s in students]
    return jsonify(result)

@app.route('/import_debts_csv', methods=['POST'])
def import_debts_csv():
    """Импорт данных о задолженностях из CSV-файла и создание уведомлений"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    file = request.files['file']
    template_type_id = request.form.get('template_type_id')
    period = request.form.get('period')
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Файл не выбран'})
    
    if not template_type_id or not period:
        return jsonify({'success': False, 'message': 'Не указан тип уведомления или период'})
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Импортируем данные из CSV
        from utils.import_export import import_debts_from_csv
        import_result = import_debts_from_csv(file_path)
        
        if not import_result['success']:
            # Удаляем временный файл
            os.remove(file_path)
            return jsonify(import_result)
        
        # Создаем уведомления
        from database.db import create_notifications_from_csv_data
        create_result = create_notifications_from_csv_data(
            import_result['data'],
            template_type_id,
            period
        )
        
        # Удаляем временный файл
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': f'Успешно создано {create_result["success"]} уведомлений, не удалось создать {create_result["failed"]} уведомлений',
            'details': create_result
        })
@app.route('/import_debts')
def import_debts_page():
    """Страница импорта задолженностей из CSV"""
    template_types = get_all_template_types()
    return render_template('import_debts.html', template_types=template_types)
@app.route('/api/get_unique_classes')
def api_get_unique_classes():
    """API для получения списка всех классов"""
    from database.db import get_unique_classes_sorted
    unique_classes = get_unique_classes_sorted()
    print(f"Запрошены классы, найдено: {unique_classes}")  # Для отладки
    return jsonify(unique_classes)
@app.route('/api/get_students_by_class/<class_name>')
def api_get_students_by_class(class_name):
    """API для получения списка учеников определенного класса"""
    from database.db import get_session, Student
    session = get_session()
    students = session.query(Student).filter_by(class_name=class_name).all()
    result = [{'id': s.id, 'full_name': s.full_name, 'class_name': s.class_name} for s in students]
    session.close()
    print(f"Найдено {len(result)} учеников в классе {class_name}")  # Для отладки
    return jsonify(result)

@app.route('/students')
def students():
    """Страница управления учениками"""
    from database.db import get_all_students_sorted
    all_students = get_all_students_sorted()
    return render_template('students.html', students=all_students)

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Изменить порт на 5001 или любой другой