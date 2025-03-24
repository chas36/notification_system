"""
Модуль обновления document_generator.py для работы с новым шаблоном уведомлений
"""
from docx import Document
import os
from datetime import datetime
from database.db import get_notification_with_details

def generate_document(notification_id):
    """Генерирует документ уведомления на основе данных из БД и нового шаблона"""
    # Получаем данные уведомления
    notification_data = get_notification_with_details(notification_id)
    
    if not notification_data:
        return {'success': False, 'message': 'Уведомление не найдено'}
    
    # Путь к единому шаблону
    template_path = 'templates/notification.docx'
    
    if not os.path.exists(template_path):
        return {'success': False, 'message': f'Шаблон не найден: {template_path}'}
    
    try:
        # Загружаем шаблон
        doc = Document(template_path)
        
        # Получаем данные для подстановки
        student = notification_data['student']
        subjects = notification_data['subjects']
        deadline_dates = notification_data['deadlines']
        
        # Определяем, является ли класс "A" классом
        is_class_a = "А" in student.class_name or "A" in student.class_name
        
        # Формируем текст уведомления
        notification_text = f"Администрация школы доводит до Вашего сведения, что учащийся {student.full_name} класса {student.class_name} по результатам промежуточной аттестации имеет:"
        
        # Находим или создаем параграф для основного текста
        main_text_found = False
        for i, paragraph in enumerate(doc.paragraphs):
            if "Уведомление" in paragraph.text:
                # Вставляем основной текст после заголовка "Уведомление"
                p = doc.add_paragraph(notification_text)
                main_text_found = True
                break
        
        if not main_text_found:
            # Если заголовок не найден, добавляем в конец документа
            doc.add_paragraph("Уведомление")
            doc.add_paragraph(notification_text)
        
        # Добавляем список предметов с неудовлетворительными оценками
        if subjects:
            # Получаем список предметов с неудовлетворительными оценками
            failed_subjects = [subject.name for subject in subjects]
            failed_subjects_text = ", ".join(failed_subjects)
            
            doc.add_paragraph(f"- неудовлетворительные отметки по предметам: {failed_subjects_text}")
            
            # Для классов, кроме "А", также добавляем удовлетворительные оценки по углубленным предметам
            if not is_class_a:
                # В реальном приложении здесь должна быть логика определения предметов с оценкой "3"
                # Это заглушка, которую нужно заменить реальными данными
                satisfactory_subjects = []  # Это нужно заполнить из базы данных
                
                if satisfactory_subjects:
                    satisfactory_subjects_text = ", ".join(satisfactory_subjects)
                    doc.add_paragraph(f"- удовлетворительные отметки по предметам, изучаемым на углубленном уровне: {satisfactory_subjects_text}")
        
        # Добавляем информацию о возможном переводе (для всех классов, кроме "А")
        if not is_class_a:
            deadline_date = notification_data.get('deadline_date', 'указанного срока')
            doc.add_paragraph(f"В случае, если данные оценки не будут исправлены до {deadline_date}, то по решению Педагогического совета в соответствии с положением школы о классах с углубленным изучением отдельных предметов может быть осуществлен перевод в общеобразовательный класс.")
        
        # Добавляем график ликвидации задолженностей, если он есть
        if deadline_dates:
            doc.add_paragraph("График ликвидации академической задолженности:")
            
            # Создаем таблицу для графика
            table = doc.add_table(rows=1, cols=3)
            table.style = 'Table Grid'
            
            # Заголовки таблицы
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = "Предмет"
            hdr_cells[1].text = "Дата"
            hdr_cells[2].text = "Тема (при наличии)"
            
            # Добавляем строки для каждого предмета
            for deadline in deadline_dates:
                row_cells = table.add_row().cells
                row_cells[0].text = deadline['subject'].name
                row_cells[1].text = deadline['date']
                row_cells[2].text = deadline.get('topic', '')
        
        # Определяем учебный год
        now = datetime.now()
        if now.month >= 9:  # Если сейчас сентябрь или позже
            academic_year = f"{now.year}-{now.year + 1}"
        else:
            academic_year = f"{now.year - 1}-{now.year}"
        
        # Заменяем плейсхолдер для учебного года, если он есть
        for paragraph in doc.paragraphs:
            if "учебного года" in paragraph.text:
                paragraph.text = paragraph.text.replace("учебного года", f"учебного года {academic_year}")
        
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