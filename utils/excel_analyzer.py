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
    

    """
    Анализирует Excel-файлы с успеваемостью и выявляет учеников с задолженностями
    и тройками по профильным предметам
    """
    # Начало функции остается без изменений...
    
    for file_path in files_list:
        # Загрузка данных из файла
        print(f"Загружаем файл: {file_path}")
        try:
            excel_data = pd.ExcelFile(file_path)
            sheet_name = excel_data.sheet_names[0]
            print(f"Используем лист: {sheet_name}")
            
            # Читаем первые несколько строк для анализа структуры
            header_data = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5, header=None)
            
            # Выводим первые строки для отладки
            print("Структура первой строки:")
            for i in range(min(5, header_data.shape[1])):
                try:
                    val = header_data.iloc[0, i]
                    print(f"  Ячейка {i+1}: {val}")
                except:
                    print(f"  Ячейка {i+1}: недоступна")
            
            # Пытаемся получить ФИО ученика из ячейки D1 (индекс 3)
            if header_data.shape[1] > 3:  # Убедимся, что есть 4-я колонка
                student_name = str(header_data.iloc[0, 3])
                if student_name == 'nan' or pd.isna(student_name):
                    # Если ячейка D1 пуста, ищем ФИО в других ячейках первой строки
                    for i in range(header_data.shape[1]):
                        val = str(header_data.iloc[0, i])
                        if len(val.split()) >= 2 and val != 'nan' and not pd.isna(val):
                            student_name = val
                            print(f"Найдено ФИО в ячейке {i+1}: {student_name}")
                            break
                else:
                    print(f"Найдено ФИО ученика в ячейке D1: {student_name}")
            else:
                # Если нет 4-й колонки, ищем в других ячейках
                student_name = "Неизвестный ученик"
                for i in range(header_data.shape[1]):
                    val = str(header_data.iloc[0, i])
                    if len(val.split()) >= 2 and val != 'nan' and not pd.isna(val):
                        student_name = val
                        print(f"Найдено ФИО в ячейке {i+1}: {student_name}")
                        break
            
            # Если не удалось найти ФИО, пробуем извлечь из имени файла
            if student_name == "Неизвестный ученик" or student_name == 'nan':
                # Извлекаем имя из имени файла
                filename = os.path.basename(file_path)
                name_match = re.search(r'Отчёт об успеваемости\.\s*(.*?)\s*\.\s*\d+', filename)
                if name_match:
                    student_name = name_match.group(1).strip()
                    print(f"Извлечено ФИО из имени файла: {student_name}")
                else:
                    student_name = os.path.splitext(os.path.basename(file_path))[0]
                    print(f"Используем имя файла как ФИО: {student_name}")
            
            # Получаем класс из данных или используем переданный класс
            if not class_name:
                # Если класс не указан в параметрах, ищем в таблице или имени файла
                file_class = "Неизвестный класс"
                
                # Ищем класс в таблице
                for i in range(min(2, header_data.shape[0])):
                    for j in range(header_data.shape[1]):
                        try:
                            val = str(header_data.iloc[i, j])
                            if re.match(r'\d+[А-Я]', val):
                                file_class = val
                                print(f"Найден класс в таблице: {file_class}")
                                break
                        except:
                            continue
                
                # Если не нашли в таблице, ищем в имени файла
                if file_class == "Неизвестный класс":
                    filename = os.path.basename(file_path)
                    class_match = re.search(r'(\d+[А-Я])', filename)
                    if class_match:
                        file_class = class_match.group(1)
                        print(f"Извлечен класс из имени файла: {file_class}")
                
                current_class = file_class
            else:
                current_class = class_name
            
            print(f"Итоговые данные для анализа: ФИО ученика: '{student_name}', Класс: '{current_class}'")
            
            # Чтение данных об успеваемости - остальная часть кода не меняется
            data = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=3)
            
            # Переименование колонок и анализ данных - без изменений...
            
            # Переименовываем колонки для удобства
            data.columns = [
                'Предмет',
                'Период промежуточной аттестации',
                'Дата промежуточной аттестации',
                'Отметки',
                'Средневзвешенный балл',
                'Итоговая отметка'
            ]
            
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