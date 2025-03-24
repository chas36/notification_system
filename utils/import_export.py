import pandas as pd
import os
import requests
import json
from database.db import import_students_from_list

def import_students_from_excel(file_path):
    """Импортирует учеников из Excel-файла"""
    try:
        df = pd.read_excel(file_path)
        
        # Проверяем наличие нужных столбцов
        required_columns = ['ФИО', 'Класс']
        for column in required_columns:
            if column not in df.columns:
                return {'success': False, 'message': f'В Excel-файле отсутствует обязательный столбец {column}'}
        
        # Преобразуем данные в нужный формат
        students_data = []
        for _, row in df.iterrows():
            students_data.append({
                'full_name': row['ФИО'],
                'class_name': str(row['Класс'])
            })
        
        # Добавляем учеников в базу данных
        added_count = import_students_from_list(students_data)
        
        return {'success': True, 'message': f'Успешно импортировано {added_count} учеников'}
    
    except Exception as e:
        return {'success': False, 'message': f'Ошибка при импорте: {str(e)}'}

def import_students_from_yandex_disk(api_token, file_path):
    """Импортирует учеников из таблицы на Яндекс.Диске"""
    try:
        # Получаем ссылку на скачивание файла
        headers = {
            'Authorization': f'OAuth {api_token}'
        }
        params = {
            'path': file_path,
            'fields': 'file'
        }
        response = requests.get('https://cloud-api.yandex.net/v1/disk/resources/download', 
                               headers=headers, params=params)
        
        if response.status_code != 200:
            return {'success': False, 'message': f'Ошибка при доступе к Яндекс.Диску: {response.text}'}
        
        download_url = response.json()['href']
        
        # Скачиваем файл во временную директорию
        temp_file_path = os.path.join('temp', 'yandex_disk_import.xlsx')
        os.makedirs('temp', exist_ok=True)
        
        file_response = requests.get(download_url)
        with open(temp_file_path, 'wb') as f:
            f.write(file_response.content)
        
        # Импортируем данные из скачанного файла
        result = import_students_from_excel(temp_file_path)
        
        # Удаляем временный файл
        os.remove(temp_file_path)
        
        return result
    
    except Exception as e:
        return {'success': False, 'message': f'Ошибка при импорте с Яндекс.Диска: {str(e)}'}
    
def import_debts_from_csv(file_path):
    """Импортирует информацию о задолженностях из CSV-файла"""
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        
        # Проверяем наличие нужных столбцов
        required_columns = ['ФИО ученика', 'Предмет', 'Период промежуточной аттестации', 
                           'Дата промежуточной аттестации', 'Итоговая отметка']
        
        for column in required_columns:
            if column not in df.columns:
                return {'success': False, 'message': f'В CSV-файле отсутствует обязательный столбец {column}'}
        
        # Группируем данные по ученикам
        debts_by_student = {}
        
        for _, row in df.iterrows():
            student_name = row['ФИО ученика']
            
            if student_name not in debts_by_student:
                debts_by_student[student_name] = []
            
            debts_by_student[student_name].append({
                'subject': row['Предмет'],
                'period': row['Период промежуточной аттестации'],
                'date': row['Дата промежуточной аттестации'],
                'grade': row['Итоговая отметка'],
            })
        
        return {
            'success': True, 
            'message': f'Успешно импортировано данных о задолженностях для {len(debts_by_student)} учеников',
            'data': debts_by_student
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Ошибка при импорте: {str(e)}'}