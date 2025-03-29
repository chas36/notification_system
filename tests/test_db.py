from database.db import get_all_students, add_student, get_student_by_id

def test_add_and_get_student(app):
    """Test adding and retrieving a student"""
    with app.app_context():
        # Добавляем нового ученика
        student_name = 'Иванов Иван Иванович'
        class_name = '10 А'
        student_id = add_student(student_name, class_name)
        
        # Получаем ученика по ID
        student = get_student_by_id(student_id)
        
        # Проверяем, что данные совпадают
        assert student is not None
        assert student.full_name == student_name
        assert student.class_name == class_name

def test_get_all_students(app):
    """Test retrieving all students"""
    with app.app_context():
        # Добавляем несколько учеников
        add_student('Петров Петр Петрович', '9 Б')
        add_student('Сидоров Сидор Сидорович', '11 В')
        
        # Получаем всех учеников
        students = get_all_students()
        
        # Проверяем, что список не пустой
        assert len(students) > 0