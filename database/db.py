from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Student, Subject, TemplateType, Notification, NotificationSubject, DeadlineDate
from config import get_config
import os

config = get_config()
DATABASE_URL = config['DATABASE_URL']

def get_engine():
    """Создаем подключение к базе данных"""
    return create_engine(DATABASE_URL)

def init_db():
    """Инициализируем базу данных"""
    # Import User model to ensure it's registered with Base
    from auth.models import User
    
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Rest of the function remains the same
    Session = sessionmaker(bind=engine)
    session = Session()

    # Добавляем стандартные предметы, если их еще нет
    standard_subjects = ["Математика", "Русский язык", "Литература", "Физика", 
                         "Химия", "Биология", "История", "Обществознание",
                         "Иностранный язык", "Информатика", "География"]
    
    for subject_name in standard_subjects:
        if not session.query(Subject).filter_by(name=subject_name).first():
            session.add(Subject(name=subject_name))
    
    # Добавляем типы шаблонов
    template_types = [
        {"name": "Задолженность по модулю", 
         "description": "Уведомление о задолженности по итогам модуля", 
         "file_path": "templates/module_notification.docx"},
        {"name": "Задолженность по триместру", 
         "description": "Уведомление о задолженности по итогам триместра", 
         "file_path": "templates/trimester_notification.docx"},
        {"name": "Уведомление по отчислению из профиля", 
         "description": "Уведомление о возможном переводе в общеобразовательный класс", 
         "file_path": "templates/profile_notification.docx"},
        {"name": "Предупреждение об отчислении из профиля", 
         "description": "Предварительное уведомление о возможном переводе в общеобразовательный класс", 
         "file_path": "templates/profile_warning_notification.docx"}
    ]
    
    for template in template_types:
        if not session.query(TemplateType).filter_by(name=template["name"]).first():
            session.add(TemplateType(**template))
    
    session.commit()
    session.close()

def get_session():
    """Возвращает сессию для работы с БД"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def get_all_students():
    """Получаем список всех учеников"""
    session = get_session()
    students = session.query(Student).all()
    session.close()
    return students

def get_student_by_id(student_id):
    """Получаем ученика по ID"""
    session = get_session()
    student = session.query(Student).filter_by(id=student_id).first()
    session.close()
    return student

def add_student(full_name, class_name):
    """Добавляем нового ученика"""
    session = get_session()
    student = Student(full_name=full_name, class_name=class_name)
    session.add(student)
    session.commit()
    student_id = student.id
    session.close()
    return student_id

def get_all_subjects():
    """Получаем список всех предметов"""
    session = get_session()
    subjects = session.query(Subject).all()
    session.close()
    return subjects

def get_all_template_types():
    """Получаем список всех типов шаблонов"""
    session = get_session()
    template_types = session.query(TemplateType).all()
    session.close()
    return template_types

def create_notification(student_id, template_type_id, period, subjects_ids, deadlines=None):
    """Создаем новое уведомление"""
    session = get_session()
    
    # Создаем уведомление
    notification = Notification(
        student_id=student_id,
        template_type_id=template_type_id,
        period=period
    )
    session.add(notification)
    session.flush()  # Получаем ID созданного уведомления
    
    # Добавляем предметы
    for subject_id in subjects_ids:
        notification_subject = NotificationSubject(
            notification_id=notification.id,
            subject_id=subject_id
        )
        session.add(notification_subject)
    
    # Добавляем даты ликвидации задолженностей, если они есть
    if deadlines:
        for deadline in deadlines:
            deadline_date = DeadlineDate(
                notification_id=notification.id,
                subject_id=deadline['subject_id'],
                date=deadline['date'],
                time=deadline.get('time', ''),  # Время может отсутствовать
                topic=deadline.get('topic', '')  # Тема может отсутствовать
            )
            session.add(deadline_date)
    
    session.commit()
    notification_id = notification.id
    session.close()
    
    return notification_id

def get_notification_with_details(notification_id):
    """Получаем уведомление со всеми связанными данными"""
    session = get_session()
    
    notification = session.query(Notification).filter_by(id=notification_id).first()
    
    if notification:
        # Получаем информацию о студенте
        student = notification.student
        
        # Получаем предметы
        subjects = []
        for ns in notification.subjects:
            subject = ns.subject
            subjects.append(subject)
        
        # Получаем даты ликвидации
        deadlines = []
        for dd in notification.deadlines:
            subject = dd.subject
            deadlines.append({
                'subject': subject,
                'date': dd.date,
                'time': dd.time,
                'topic': dd.topic
            })
        
        # Сохраняем всё в словарь
        result = {
            'id': notification.id,
            'student': student,
            'template_type': notification.template_type,
            'period': notification.period,
            'subjects': subjects,
            'deadlines': deadlines,
            'created_at': notification.created_at
        }
    else:
        result = None
    
    session.close()
    return result

def import_students_from_list(students_data):
    """Импортирует список учеников из списка словарей"""
    session = get_session()
    
    added_count = 0
    for student_data in students_data:
        # Проверяем, существует ли уже ученик с таким именем и классом
        existing_student = session.query(Student).filter_by(
            full_name=student_data['full_name'],
            class_name=student_data['class_name']
        ).first()
        
        if not existing_student:
            student = Student(
                full_name=student_data['full_name'],
                class_name=student_data['class_name']
            )
            session.add(student)
            added_count += 1
    
    session.commit()
    session.close()
    
    return added_count

def get_subject_by_name(subject_name):
    """Получает предмет по названию или создает новый"""
    session = get_session()
    subject = session.query(Subject).filter_by(name=subject_name).first()
    
    if not subject:
        subject = Subject(name=subject_name)
        session.add(subject)
        session.commit()
    
    subject_id = subject.id
    session.close()
    return subject_id

def create_notifications_from_csv_data(debts_by_student, template_type_id, period):
    """Создает уведомления на основе данных из CSV"""
    results = {
        'success': 0,
        'failed': 0,
        'failed_students': []
    }
    
    for student_name, debts in debts_by_student.items():
        # Поиск ученика по имени
        session = get_session()
        student = session.query(Student).filter_by(full_name=student_name).first()
        session.close()
        
        if not student:
            results['failed'] += 1
            results['failed_students'].append({
                'name': student_name,
                'reason': 'Ученик не найден в базе данных'
            })
            continue
        
        # Получаем предметы и формируем сроки ликвидации
        subject_ids = []
        deadlines = []
        
        for debt in debts:
            subject_id = get_subject_by_name(debt['subject'])
            subject_ids.append(subject_id)
            
            # Если указана дата, добавляем в график ликвидации
            if debt['date']:
                deadlines.append({
                    'subject_id': subject_id,
                    'date': debt['date'],
                    'time': '',
                    'topic': debt['period']
                })
        
        # Создаем уведомление
        try:
            notification_id = create_notification(
                student.id, 
                template_type_id,
                period,
                subject_ids,
                deadlines
            )
            
            results['success'] += 1
        except Exception as e:
            results['failed'] += 1
            results['failed_students'].append({
                'name': student_name,
                'reason': str(e)
            })
    
    return results

def get_unique_classes_sorted():
    """Получает список всех классов, отсортированных по параллели и букве"""
    session = get_session()
    students = session.query(Student).all()
    session.close()
    
    # Собираем уникальные названия классов
    class_names = set(s.class_name for s in students)
    
    # Функция для извлечения номера параллели и буквы класса
    def extract_class_components(class_name):
        # Разделяем номер и букву
        import re
        match = re.match(r'(\d+)\s*([А-Яа-яA-Za-z]*)', class_name.strip())
        if match:
            try:
                number = int(match.group(1))  # Номер параллели
                letter = match.group(2) or ""  # Буква класса (может отсутствовать)
                return (number, letter)
            except ValueError:
                # Если не удалось преобразовать в число, возвращаем большое число для сортировки в конец
                return (999, class_name)
        else:
            # Если формат не соответствует ожидаемому, возвращаем для сортировки в конец
            return (999, class_name)
    
    # Сортируем классы по параллели и букве
    sorted_classes = sorted(class_names, key=extract_class_components)
    
    return sorted_classes
    
    
def get_students_by_class_sorted(class_name):
    """Получает список учеников определенного класса, отсортированных по ФИО"""
    session = get_session()
    students = session.query(Student).filter_by(class_name=class_name).all()
    session.close()
    
    # Сортируем учеников по ФИО
    sorted_students = sorted(students, key=lambda s: s.full_name)
    
    return sorted_students
def get_all_students_sorted():
    """Получаем список всех учеников, отсортированных по классу и ФИО"""
    session = get_session()
    students = session.query(Student).all()
    session.close()
    
    # Функция для извлечения номера параллели и буквы класса
    def extract_class_components(class_name):
        parts = class_name.strip().split()
        if len(parts) == 2:
            try:
                number = int(parts[0])  # Номер параллели
                letter = parts[1]       # Буква класса
                return (number, letter)
            except ValueError:
                return (999, class_name)
        else:
            return (999, class_name)
    
    # Сортируем учеников сначала по классу, потом по ФИО
    sorted_students = sorted(students, 
                            key=lambda s: (extract_class_components(s.class_name), s.full_name))
    
    return sorted_students

def get_schedule_times():
    """Получает расписание звонков"""
    return [
        {"id": 1, "name": "1 урок", "start": "8:30", "end": "9:15"},
        {"id": 2, "name": "2 урок", "start": "9:30", "end": "10:15"},
        {"id": 3, "name": "3 урок", "start": "10:30", "end": "11:15"},
        {"id": 4, "name": "4 урок", "start": "11:30", "end": "12:15"},
        {"id": 5, "name": "5 урок", "start": "12:25", "end": "13:10"},
        {"id": 6, "name": "6 урок", "start": "13:30", "end": "14:15"},
        {"id": 7, "name": "7 урок", "start": "14:35", "end": "15:20"},
        {"id": 8, "name": "8 урок", "start": "15:30", "end": "16:15"},
        {"id": 9, "name": "9 урок", "start": "16:25", "end": "17:10"},
        {"id": 10, "name": "10 урок", "start": "17:20", "end": "18:05"}
    ]

def get_subjects_by_grade():
    """Получает список предметов по классам"""
    return {
        "5": ["Иностранный (английский) язык", "Биология", "География", "Изобразительное искусство", 
              "История", "Литература", "Математика", "Музыка", "Основы духовно-нравственной культуры", 
              "Русский язык", "Труд (технология)", "Физическая культура"],
        "6": ["Иностранный (английский) язык", "Биология", "География", "Изобразительное искусство", 
              "Информатика", "История", "Литература", "Математика", "Музыка", "Обществознание", 
              "Русский язык", "Труд (технология)", "Физическая культура"],
        "7": ["Алгебра", "Иностранный (английский) язык", "Биология", "Вероятность и статистика", 
              "География", "Геометрия", "Информатика", "История", "Литература", "Обществознание", 
              "Русский язык", "Труд (технология)", "Физика", "Физическая культура"],
        "8": ["Алгебра", "Иностранный (английский) язык", "Биология", "Вероятность и статистика", 
              "География", "Геометрия", "Информатика", "История", "Литература", "Обществознание", 
              "Основы безопасности и защиты", "Русский язык", "Труд (технология)", "Физика", 
              "Физическая культура", "Химия"],
        "9": ["География", "Информатика", "Математика", "Обществознание", "Русский язык", "Алгебра", 
              "Иностранный (английский) язык", "Биология", "Вероятность и статистика", "Геометрия", 
              "История", "Литература", "Основы безопасности и защиты", "Проектно-исследовательская деятельность", 
              "Труд (технология)", "Физика", "Физическая культура", "Химия"],
        "10": ["Алгебра и начала математического анализа", "Иностранный (английский) язык", "Биология", 
               "Вероятность и статистика", "География", "Геометрия", "Индивидуальный проект", "Информатика", 
               "История", "Литература", "Математика", "Обществознание", "Основы безопасности и защиты", 
               "Русский язык", "Физика", "Физическая культура", "Химия"],
        "11": ["Алгебра и начала математического анализа", "Иностранный (английский) язык", "Биология", 
               "Вероятность и статистика", "География", "Геометрия", "Иностранный язык", "Информатика", 
               "История", "Литература", "Математика", "Обществознание", "Основы безопасности и защиты", 
               "Практикум ЕГЭ", "Русский язык", "Физика", "Физическая культура", "Химия"]
    }

def get_subject_by_name(subject_name):
    """Получает ID предмета по имени или создает новый"""
    session = get_session()
    subject = session.query(Subject).filter_by(name=subject_name).first()
    
    if not subject:
        subject = Subject(name=subject_name)
        session.add(subject)
        session.flush()
        
    subject_id = subject.id
    session.commit()
    session.close()
    
    return subject_id
def get_student_by_name(student_name):
    """Получает ученика по ФИО"""
    session = get_session()
    student = session.query(Student).filter_by(full_name=student_name).first()
    session.close()
    return student