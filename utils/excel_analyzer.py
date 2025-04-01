# utils/excel_analyzer.py

import pandas as pd
import os
import re
from database.db import get_session
from database.models import ClassProfile, Subject

def get_profile_subjects_for_class(class_name):
    """Получает список профильных предметов для указанного класса"""
    session = get_session()
    
    # Получаем ID профильных предметов для класса
    from database.models import ClassProfile
    profile_records = session.query(ClassProfile).filter_by(class_name=class_name).all()
    subject_ids = [record.subject_id for record in profile_records]
    
    # Получаем названия предметов
    subjects = []
    if subject_ids:
        subjects = session.query(Subject).filter(Subject.id.in_(subject_ids)).all()
        subjects = [subject.name for subject in subjects]
    
    session.close()
    return subjects

def analyze_excel_files(folder_path, class_name=None):
    """
    Анализирует Excel-файлы с успеваемостью и выявляет учеников с задолженностями
    и тройками по профильным предметам
    
    Args:
        folder_path: путь к папке с Excel-файлами
        class_name: название класса (если указано, используются профильные предметы этого класса)
    
    Returns:
        students_with_problems: список словарей с данными учеников и их проблемами
    """
    # Получаем список профильных предметов для указанного класса, если класс указан
    subjects_of_interest = []
    if class_name:
        subjects_of_interest = get_profile_subjects_for_class(class_name)
    
    # Если профильные предметы не найдены (или класс не указан), используем предметы по умолчанию
    if not subjects_of_interest:
        subjects_of_interest = [
            'Алгебра', 'Геометрия', 'Физика', 'Информатика', 
            'Вероятность и статистика', 'Труд (технология)'
        ]
    
    # Списки для хранения результатов
    students_with_threes = []
    students_with_failures = []
    
    # Получение списка всех файлов Excel в указанной папке
    print(f"Получаем список всех файлов в папке: {folder_path}")
    files_list = [os.path.join(folder_path, file) for file in os.listdir(folder_path) 
                 if file.endswith('.xlsx') or file.endswith('.xls')]
    print(f"Найдено {len(files_list)} файлов Excel для обработки.")
    
    for file_path in files_list:
        # Загрузка данных из файла
        print(f"Загружаем файл: {file_path}")
        try:
            excel_data = pd.ExcelFile(file_path)
            sheet_name = excel_data.sheet_names[0]  # Предполагается, что нужная информация в первом листе
            print(f"Используем лист: {sheet_name}")
            data = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=3)
            
            # Переименовываем колонки для удобства
            data.columns = [
                'Предмет',
                'Период промежуточной аттестации',
                'Дата промежуточной аттестации',
                'Отметки',
                'Средневзвешенный балл',
                'Итоговая отметка'
            ]
            
            # Извлекаем имя ученика из имени файла
            match = re.search(r'Отчёт об успеваемости\.\s*(.*?)\s*\.\s*\d+-?[А-Яа-я]', os.path.basename(file_path))
            if match:
                student_name = match.group(1)
            else:
                # Используем более надежный алгоритм разбора имени файла
                filename = os.path.basename(file_path)
                parts = filename.split('.')
                
                # Если файл разделен точками и первая часть - "Отчёт об успеваемости"
                if len(parts) > 2 and 'успеваемости' in parts[0]:
                    student_name = parts[1].strip()
                else:
                    # Пытаемся извлечь имя по другому алгоритму
                    student_name = re.sub(r'^Отчёт об успеваемости\s*\.?\s*', '', filename)
                    student_name = re.sub(r'\s*\.\s*\d+-?[А-Яа-я].*$', '', student_name)
                    
                # Проверяем, что имя не пустое и не состоит только из класса
                if not student_name or re.match(r'^\d+-?[А-Яа-я]$', student_name):
                    # Если не удалось извлечь имя, используем имя файла без расширения
                    student_name = os.path.splitext(filename)[0]
            
            print(f"Имя ученика: {student_name}")
            
            # Извлекаем класс ученика, если не указан явно
            if not class_name:
                class_match = re.search(r'(\d+[А-Яа-я])', os.path.basename(file_path))
                if class_match:
                    extracted_class = class_match.group(1)
                    current_class = extracted_class
                else:
                    current_class = None
            else:
                current_class = class_name
            
            # Проходим по всем строкам и ищем тройки и задолженности
            previous_grade = None
            current_subject = None
            
            for index, row in data.iterrows():
                # Если в колонке 'Предмет' есть значение, это название нового предмета
                if pd.notna(row['Предмет']):
                    current_subject = row['Предмет']
                    previous_grade = None  # Сброс предыдущей оценки при смене предмета
                    print(f"Обрабатываем предмет: {current_subject}")
                
                # Проверяем, интересующий ли нас предмет, и существует ли оценка 'Итоговая отметка'
                if current_subject in subjects_of_interest and pd.notna(row['Итоговая отметка']):
                    current_grade = row['Итоговая отметка']
                    
                    # Проверка на задолженность (оценка < 3)
                    if current_grade < 3:
                        students_with_failures.append({
                            'ФИО ученика': student_name,
                            'Класс': current_class,
                            'Предмет': current_subject,
                            'Период промежуточной аттестации': row['Период промежуточной аттестации'],
                            'Дата промежуточной аттестации': row['Дата промежуточной аттестации'],
                            'Итоговая отметка': current_grade,
                            'Тип проблемы': 'Задолженность'
                        })
                    
                    # Логика исключения, если следующая оценка выше тройки
                    if previous_grade == 3 and current_grade > 3:
                        # Если предыдущая оценка была тройкой, но следующая улучшилась - исключаем
                        students_with_threes = [entry for entry in students_with_threes if not (
                            entry['ФИО ученика'] == student_name and 
                            entry['Предмет'] == current_subject and 
                            entry['Итоговая отметка'] == 3
                        )]
                    elif current_grade == 3:
                        # Добавляем запись, если текущая оценка - тройка
                        students_with_threes.append({
                            'ФИО ученика': student_name,
                            'Класс': current_class,
                            'Предмет': current_subject,
                            'Период промежуточной аттестации': row['Период промежуточной аттестации'],
                            'Дата промежуточной аттестации': row['Дата промежуточной аттестации'],
                            'Итоговая отметка': current_grade,
                            'Тип проблемы': 'Тройка'
                        })
                    
                    # Обновляем предыдущую оценку
                    previous_grade = current_grade
        
        except Exception as e:
            print(f"Ошибка при обработке файла {file_path}: {str(e)}")
            continue
    
    # Объединяем списки с тройками и задолженностями
    all_problems = students_with_threes + students_with_failures
    
    # Создаем DataFrame для удобного отображения результатов
    if all_problems:
        result_df = pd.DataFrame(all_problems)
        print("Ученики с проблемами по интересующим предметам:")
        print(result_df[['ФИО ученика', 'Класс', 'Предмет', 'Период промежуточной аттестации', 'Итоговая отметка', 'Тип проблемы']])
        
        # Возвращаем список с проблемами
        return all_problems
    else:
        print("Не найдено проблем по интересующим предметам.")
        return []

def save_results_to_csv(results, output_path='students_with_problems.csv'):
    """Сохраняет результаты анализа в CSV-файл"""
    if results:
        result_df = pd.DataFrame(results)
        result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"Результаты сохранены в файл '{output_path}'")
        return output_path
    else:
        print("Нет результатов для сохранения.")
        return None