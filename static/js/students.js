document.addEventListener('DOMContentLoaded', function() {
    // Форма добавления ученика
    const addStudentForm = document.getElementById('addStudentForm');
    if (addStudentForm) {
        addStudentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(addStudentForm);
            
            fetch('/admin/add_student', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Успешно', data.message, 'success');
                    addStudentForm.reset();
                    // Перезагружаем страницу для обновления списка
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showToast('Ошибка', data.message, 'error');
                }
            })
            .catch(error => {
                showToast('Ошибка', 'Ошибка при выполнении запроса', 'error');
            });
        });
    }
    
    // Форма импорта из Excel
    const importExcelForm = document.getElementById('importExcelForm');
    if (importExcelForm) {
        importExcelForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(importExcelForm);
            
            // Показываем индикатор загрузки
            const submitBtn = importExcelForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Загрузка...';
            submitBtn.disabled = true;
            
            fetch('/admin/import_from_excel', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                // Возвращаем кнопку в исходное состояние
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                
                if (data.success) {
                    showToast('Успешно', data.message, 'success');
                    importExcelForm.reset();
                    // Перезагружаем страницу для обновления списка
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showToast('Ошибка', data.message, 'error');
                }
            })
            .catch(error => {
                // Возвращаем кнопку в исходное состояние
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                showToast('Ошибка', 'Ошибка при выполнении запроса', 'error');
            });
        });
    }
    
    // Обработчик для поиска по таблице
    const searchStudent = document.getElementById('searchStudent');
    if (searchStudent) {
        searchStudent.addEventListener('input', function() {
            searchTable('studentsTable', this);
        });
        
        // Обработчик для кнопки очистки поиска
        const clearSearch = document.getElementById('clearSearch');
        if (clearSearch) {
            clearSearch.addEventListener('click', function() {
                searchStudent.value = '';
                searchTable('studentsTable', searchStudent);
            });
        }
    }
    
    // Обработчик для сохранения редактирования
    const saveEditStudent = document.getElementById('saveEditStudent');
    if (saveEditStudent) {
        saveEditStudent.addEventListener('click', function() {
            const editForm = document.getElementById('editStudentForm');
            const formData = new FormData(editForm);
            
            fetch('/admin/update_student', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Закрываем модальное окно
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editStudentModal'));
                    modal.hide();
                    
                    showToast('Успешно', data.message, 'success');
                    
                    // Перезагружаем страницу для обновления списка
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showToast('Ошибка', data.message, 'error');
                }
            })
            .catch(error => {
                showToast('Ошибка', 'Ошибка при выполнении запроса', 'error');
            });
        });
    }
    
    // Делаем таблицу сортируемой, если такая функция есть
    if (typeof makeSortable === 'function') {
        makeSortable('studentsTable');
    }
});

// Функция для редактирования ученика
function editStudent(studentId) {
    fetch(`/admin/get_student/${studentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const student = data.student;
                
                document.getElementById('editStudentId').value = student.id;
                document.getElementById('editFullName').value = student.full_name;
                document.getElementById('editClassName').value = student.class_name;
                
                // Открываем модальное окно
                const modal = new bootstrap.Modal(document.getElementById('editStudentModal'));
                modal.show();
            } else {
                showToast('Ошибка', data.message, 'error');
            }
        })
        .catch(error => {
            showToast('Ошибка', 'Ошибка при получении данных', 'error');
        });
}

// Функция для удаления ученика
function deleteStudent(studentId) {
    if (confirm('Вы уверены, что хотите удалить этого ученика?')) {
        fetch(`/admin/delete_student/${studentId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Успешно', data.message, 'success');
                
                // Удаляем строку из таблицы
                const row = document.querySelector(`#studentsTable tr td:first-child:contains(${studentId})`).parentNode;
                row.remove();
            } else {
                showToast('Ошибка', data.message, 'error');
            }
        })
        .catch(error => {
            showToast('Ошибка', 'Ошибка при выполнении запроса', 'error');
        });
    }
}

// Функция для создания уведомления для ученика
function createNotificationForStudent(studentId) {
    window.location.href = `/create_notification?student_id=${studentId}`;
}
// Обработчики для кнопок переключения вида
const listViewBtn = document.getElementById('listView');
const groupViewBtn = document.getElementById('groupView');

if (listViewBtn && groupViewBtn) {
    listViewBtn.addEventListener('click', function() {
        this.classList.add('active');
        groupViewBtn.classList.remove('active');
        showListView();
    });
    
    groupViewBtn.addEventListener('click', function() {
        this.classList.add('active');
        listViewBtn.classList.remove('active');
        showGroupView();
    });
}

// Функция для отображения простого списка
function showListView() {
    const tableContainer = document.querySelector('.table-responsive');
    tableContainer.innerHTML = `
        <table class="table table-striped table-hover">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>ФИО</th>
                    <th>Класс</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody id="studentsTable">
                <!-- Здесь будут ученики -->
            </tbody>
        </table>
    `;
    
    // Загружаем всех учеников
    fetch('/api/get_students')
        .then(response => response.json())
        .then(students => {
            const tbody = document.getElementById('studentsTable');
            students.forEach(student => {
                tbody.appendChild(createStudentRow(student));
            });
        });
}

// Функция для отображения учеников по группам
function showGroupView() {
    const tableContainer = document.querySelector('.table-responsive');
    tableContainer.innerHTML = '<div id="classGroups"></div>';
    
    // Загружаем классы
    fetch('/api/get_unique_classes')
        .then(response => response.json())
        .then(classes => {
            const container = document.getElementById('classGroups');
            
            // Для каждого класса создаем таблицу
            classes.forEach(className => {
                const classDiv = document.createElement('div');
                classDiv.className = 'mb-4';
                classDiv.innerHTML = `
                    <h3 class="h5">${className}</h3>
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>ФИО</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody id="class-${className.replace(/\s+/g, '-')}">
                            <!-- Здесь будут ученики класса -->
                        </tbody>
                    </table>
                `;
                container.appendChild(classDiv);
                
                // Загружаем учеников для класса
                fetch(`/api/get_students_by_class/${encodeURIComponent(className)}`)
                    .then(response => response.json())
                    .then(students => {
                        const tbody = document.getElementById(`class-${className.replace(/\s+/g, '-')}`);
                        students.forEach(student => {
                            tbody.appendChild(createStudentRowNoClass(student));
                        });
                    });
            });
        });
}

// Функция для создания строки таблицы ученика (с классом)
function createStudentRow(student) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td>${student.id}</td>
        <td>${student.full_name}</td>
        <td>${student.class_name}</td>
        <td>
            <button class="btn btn-sm btn-info" onclick="editStudent(${student.id})">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-sm btn-danger" onclick="deleteStudent(${student.id})">
                <i class="bi bi-trash"></i>
            </button>
            <button class="btn btn-sm btn-success" onclick="createNotificationForStudent(${student.id})">
                <i class="bi bi-file-earmark-text"></i>
            </button>
        </td>
    `;
    return tr;
}

// Функция для создания строки таблицы ученика (без класса)
function createStudentRowNoClass(student) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td>${student.id}</td>
        <td>${student.full_name}</td>
        <td>
            <button class="btn btn-sm btn-info" onclick="editStudent(${student.id})">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-sm btn-danger" onclick="deleteStudent(${student.id})">
                <i class="bi bi-trash"></i>
            </button>
            <button class="btn btn-sm btn-success" onclick="createNotificationForStudent(${student.id})">
                <i class="bi bi-file-earmark-text"></i>
            </button>
        </td>
    `;
    return tr;
}