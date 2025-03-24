from docx import Document
import os
from datetime import datetime
from database.db import import_students_from_list
from database.db import get_notification_with_details

def generate_document(notification_id):
    """Генерирует документ уведомления на основе данных из БД"""
    # Получаем данные уведомления
    notification_data = get_notification_with_details(notification_id)
    
    if not notification_data:
        return {'success': False, 'message': 'Уведомление не найдено'}
    
    # Получаем путь к шаблону
    template_path = notification_data['template_type'].file_path
    
    if not os.path.exists(template_path):
        return {'success': False, 'message': f'Шаблон не найден: {template_path}'}
    
    try:
        # Загружаем шаблон
        doc = Document(template_path)
        
        # Заполняем общие данные
        student = notification_data['student']
        
        # Определяем текущий учебный год
        now = datetime.now()
        if now.month >= 9:  # Если сейчас сентябрь или позже
            academic_year = f"{now.year}-{now.year + 1}"
        else:
            academic_year = f"{now.year - 1}-{now.year}"
        
        # Замены в тексте документа для всех типов шаблонов
        replacements = {
            '_____модуля': notification_data['period'],
            '_____ модуля': notification_data['period'],
            '______ "____"': f"{student.class_name}",
            '________ "____"': f"{student.class_name}",
            '_______модуля': notification_data['period'],
            '_____ триместра': notification_data['period'],
            'учебного года': f"учебного года {academic_year}",
            '____триместра': notification_data['period'],
            '2023-2024': academic_year,
            '2024-2025': academic_year,
        }
        
        # Находим все текстовые блоки и заменяем плейсхолдеры
        for paragraph in doc.paragraphs:
            for key, value in replacements.items():
                if key in paragraph.text:
                    paragraph.text = paragraph.text.replace(key, value)
            
            # Заменяем ФИО ученика
            if '_________________' in paragraph.text:
                paragraph.text = paragraph.text.replace('_________________', student.full_name)
        
        # Заполняем список предметов
        subjects = notification_data['subjects']
        bullet_points_found = False
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip() == '-':
                bullet_points_found = True
                # Удаляем существующую маркированную строку
                p = paragraph._p
                p.getparent().remove(p)
                break
        
        if bullet_points_found:
            # Находим место, где нужно добавить список предметов
            for i, paragraph in enumerate(doc.paragraphs):
                if 'имеет академическую задолженность' in paragraph.text or 'неудовлетворительную' in paragraph.text:
                    # Добавляем список предметов после этого параграфа
                    for subject in subjects:
                        doc.add_paragraph(f"- {subject.name}", style='List Bullet')
                    break
        
        # Если есть график ликвидации задолженностей, заполняем его
        deadlines = notification_data['deadlines']
        if deadlines:
            # Ищем таблицу с графиком
            for table in doc.tables:
                # Проверяем, что это нужная таблица
                if table.rows[0].cells[0].text.strip() in ["Дата", "Предмет", "Предмет                ", "Дата         "]:
                    # Очищаем все строки таблицы, кроме заголовка
                    while len(table.rows) > 1:
                        table._tbl.remove(table.rows[-1]._tr)
                    
                    # Добавляем строки с данными о сроках
                    for deadline in deadlines:
                        row = table.add_row()
                        
                        # Определяем индексы столбцов в зависимости от типа таблицы
                        subject_idx = 0
                        date_idx = 1
                        time_idx = None
                        topic_idx = 2
                        
                        if table.rows[0].cells[0].text.strip() == "Дата":
                            date_idx = 0
                            time_idx = 1
                            topic_idx = 2
                            subject_idx = None
                        
                        if subject_idx is not None:
                            row.cells[subject_idx].text = deadline['subject'].name
                        
                        row.cells[date_idx].text = deadline['date']
                        
                        if time_idx is not None and 'time' in deadline:
                            row.cells[time_idx].text = deadline['time']
                        
                        if 'topic' in deadline and deadline['topic']:
                            row.cells[topic_idx].text = deadline['topic']
        
        # Создаем директорию для сохранения результатов, если её нет
        output_dir = 'generated_documents'
        os.makedirs(output_dir, exist_ok=True)
        
        # Формируем имя файла
        file_name = f"{student.full_name}_{student.class_name}_{notification_data['period']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        file_path = os.path.join(output_dir, file_name)
        
        # Сохраняем документ
        doc.save(file_path)
        
        return {
            'success': True, 
            'message': 'Документ успешно создан', 
            'file_path': file_path,
            'file_name': file_name
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Ошибка при генерации документа: {str(e)}'}

