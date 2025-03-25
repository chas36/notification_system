// static/js/notification_form.js

document.addEventListener('DOMContentLoaded', function() {
    // Элементы формы
    const form = document.getElementById('notificationForm');
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const goToStep2Button = document.getElementById('goToStep2');
    const goToStep3Button = document.getElementById('goToStep3');
    const backToStep1Button = document.getElementById('backToStep1');
    const backToStep2Button = document.getElementById('backToStep2');
    const templateSelect = document.getElementById('templateType');
    const templateDescription = document.getElementById('templateDescription');
    const periodTypeSelect = document.getElementById('periodType');
    const periodSelect = document.getElementById('period');
    const classSelect = document.getElementById('classSelect');
    const studentSelect = document.getElementById('studentSelect');
    const needConsultationsCheckbox = document.getElementById('needConsultationsSchedule');
    const needDeadlineCheckbox = document.getElementById('needDeadline');
    const deadlineSection = document.getElementById('deadlineSection');
    const satisfactorySubjectsSection = document.getElementById('satisfactorySubjectsSection');
    
    // Загружаем список классов
    loadClasses();
    
    // Обработчики событий для многошаговой формы
    goToStep2Button.addEventListener('click', validateAndGoToStep2);
    goToStep3Button.addEventListener('click', validateAndGoToStep3);
    backToStep1Button.addEventListener('click', goToStep1);
    backToStep2Button.addEventListener('click', goToStep2);
    
    // Обработчик изменения типа шаблона
    templateSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        templateDescription.textContent = selectedOption.dataset.description || '';
    });
    
    // Обработчик изменения типа периода
    periodTypeSelect.addEventListener('change', function() {
        const type = this.value;
        
        // Очищаем и отключаем список периодов, если тип не выбран
        periodSelect.innerHTML = '';
        
        if (!type) {
            periodSelect.disabled = true;
            periodSelect.innerHTML = '<option value="">Сначала выберите тип периода</option>';
            return;
        }
        
        // Включаем список и заполняем его вариантами в зависимости от типа
        periodSelect.disabled = false;
        
        if (type === 'module') {
            // Для модулей добавляем варианты от 1 до 5
            for (let i = 1; i <= 5; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `${i}-й модуль`;
                periodSelect.appendChild(option);
            }
        } else if (type === 'trimester') {
            // Для триместров добавляем варианты от 1 до 3
            for (let i = 1; i <= 3; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `${i}-й триместр`;
                periodSelect.appendChild(option);
            }
        }
    });
    
    // Обработчик изменения класса
    classSelect.addEventListener('change', function() {
        const className = this.value;
        
        // Очищаем и отключаем список учеников, если класс не выбран
        studentSelect.innerHTML = '';
        
        if (!className) {
            studentSelect.disabled = true;
            studentSelect.innerHTML = '<option value="">Сначала выберите класс</option>';
            return;
        }
        
        // Включаем список и загружаем учеников данного класса
        studentSelect.disabled = false;
        loadStudentsByClass(className);
        
        // Определяем, является ли класс "А" классом
        const isClassA = className.includes('А') || className.includes('A');
        
        // Показываем/скрываем секцию удовлетворительных оценок в зависимости от класса
        if (isClassA) {
            satisfactorySubjectsSection.classList.add('d-none');
        } else {
            satisfactorySubjectsSection.classList.remove('d-none');
        }
    });
    
    // Обработчик изменения чекбокса графика консультаций
    needConsultationsCheckbox.addEventListener('change', function() {
        if (this.checked) {
            goToStep3Button.textContent = 'Перейти к графику консультаций';
        } else {
            goToStep3Button.textContent = 'Продолжить';
        }
    });
    
    // Обработчик изменения чекбокса крайнего срока
    needDeadlineCheckbox.addEventListener('change', function() {
        if (this.checked) {
            deadlineSection.classList.remove('d-none');
        } else {
            deadlineSection.classList.add('d-none');
        }
    });
    
    // Обработчик отправки формы
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Проверка выбора предметов
        const failedSubjects = document.querySelectorAll('input[name="failed_subjects[]"]:checked');
        if (failedSubjects.length === 0) {
            showToast('Ошибка', 'Выберите хотя бы один предмет с задолженностью', 'error');
            return;
        }
        
        // Собираем данные формы
        const formData = new FormData(form);
        
        // Отправляем данные на сервер
        fetch('/submit_notification', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Скрываем форму и показываем результат
                form.closest('.card').classList.add('d-none');
                const resultSection = document.getElementById('resultSection');
                resultSection.classList.remove('d-none');
                
                // Настраиваем ссылку для скачивания
                const downloadLink = document.getElementById('downloadLink');
                downloadLink.href = `/download_document/${data.file_name}`;
                
                showToast('Успешно', 'Уведомление успешно создано', 'success');
            } else {
                showToast('Ошибка', data.message, 'error');
            }
        })
        .catch(error => {
            showToast('Ошибка', 'Произошла ошибка при выполнении запроса', 'error');
        });
    });
    
    // Функция валидации и перехода к шагу 2
    function validateAndGoToStep2() {
        // Проверяем обязательные поля
        const templateType = templateSelect.value;
        const periodType = periodTypeSelect.value;
        const period = periodSelect.value;
        const classValue = classSelect.value;
        const student = studentSelect.value;
        
        if (!templateType || !periodType || !period || !classValue || !student) {
            showToast('Ошибка', 'Заполните все обязательные поля', 'error');
            return;
        }
        
        // Переходим к шагу 2
        goToStep2();
        
        // Загружаем предметы для выбранного класса
        loadSubjectsByClass(classValue);
    }
    
    // Функция валидации и перехода к шагу 3
    function validateAndGoToStep3() {
        // Проверяем выбор предметов
        const failedSubjects = document.querySelectorAll('input[name="failed_subjects[]"]:checked');
        if (failedSubjects.length === 0) {
            showToast('Ошибка', 'Выберите хотя бы один предмет с задолженностью', 'error');
            return;
        }
        
        // Если график консультаций не нужен, пропускаем шаг 3 и отправляем форму
        if (!needConsultationsCheckbox.checked) {
            form.dispatchEvent(new Event('submit'));
            return;
        }
        
        // Иначе переходим к шагу 3 и генерируем форму для графика консультаций
        goToStep3();
        generateConsultationsScheduleForm();
    }
    
    // Функция перехода к шагу 1
    function goToStep1() {
        step1.classList.remove('d-none');
        step2.classList.add('d-none');
        step3.classList.add('d-none');
    }
    
    // Функция перехода к шагу 2
    function goToStep2() {
        step1.classList.add('d-none');
        step2.classList.remove('d-none');
        step3.classList.add('d-none');
    }
    
    // Функция перехода к шагу 3
    function goToStep3() {
        step1.classList.add('d-none');
        step2.classList.add('d-none');
        step3.classList.remove('d-none');
    }
    
    // Функция загрузки списка классов
    function loadClasses() {
        fetch('/api/get_unique_classes')
            .then(response => response.json())
            .then(classes => {
                classSelect.innerHTML = '<option value="">Выберите класс</option>';
                
                classes.forEach(className => {
                    const option = document.createElement('option');
                    option.value = className;
                    option.textContent = className;
                    classSelect.appendChild(option);
                });
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить список классов', 'error');
            });
    }
    
    // Функция загрузки учеников по классу
    function loadStudentsByClass(className) {
        fetch(`/api/get_students_by_class/${encodeURIComponent(className)}`)
            .then(response => response.json())
            .then(students => {
                studentSelect.innerHTML = '';
                
                if (students.length === 0) {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'Нет учеников в этом классе';
                    studentSelect.appendChild(option);
                } else {
                    const defaultOption = document.createElement('option');
                    defaultOption.value = '';
                    defaultOption.textContent = 'Выберите ученика';
                    studentSelect.appendChild(defaultOption);
                    
                    students.forEach(student => {
                        const option = document.createElement('option');
                        option.value = student.id;
                        option.textContent = student.full_name;
                        option.dataset.className = student.class_name;
                        studentSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить список учеников', 'error');
            });
    }
    
    // Функция загрузки предметов по классу
    function loadSubjectsByClass(className) {
        // Извлекаем номер класса (параллель)
        const gradeMatch = className.match(/^(\d+)/);
        if (!gradeMatch || !gradeMatch[1]) {
            showToast('Ошибка', 'Не удалось определить параллель класса', 'error');
            return;
        }
        
        const grade = gradeMatch[1];
        
        fetch(`/api/get_subjects_by_grade/${grade}`)
            .then(response => response.json())
            .then(subjects => {
                // Заполняем список предметов с академическими задолженностями
                const failedSubjectsContainer = document.getElementById('failedSubjectsContainer');
                failedSubjectsContainer.innerHTML = '';
                
                // Заполняем список предметов с удовлетворительными оценками
                const satisfactorySubjectsContainer = document.getElementById('satisfactorySubjectsContainer');
                satisfactorySubjectsContainer.innerHTML = '';
                
                subjects.forEach((subject, index) => {
                    // Добавляем в список задолженностей
                    const failedCol = document.createElement('div');
                    failedCol.className = 'col-md-4 mb-3';
                    failedCol.innerHTML = `
                        <div class="subject-item">
                            <div class="form-check">
                                <input class="form-check-input subject-checkbox" type="checkbox" 
                                    value="${subject}" id="failed_${index}" name="failed_subjects[]">
                                <label class="form-check-label" for="failed_${index}">
                                    ${subject}
                                </label>
                            </div>
                            <div class="ms-4 mt-2 subject-details d-none">
                                <div class="mb-2">
                                    <label class="form-label small">Количество тем с задолженностью:</label>
                                    <input type="number" class="form-control form-control-sm" 
                                        name="failed_topics_count_${subject.replace(/\s+/g, '_')}" min="1" value="1">
                                </div>
                            </div>
                        </div>
                    `;
                    failedSubjectsContainer.appendChild(failedCol);
                    
                    // Добавляем чекбокс в список удовлетворительных оценок
                    // (только для классов без литеры "А")
                    const isClassA = className.includes('А') || className.includes('A');
                    if (!isClassA) {
                        const satisfactoryCol = document.createElement('div');
                        satisfactoryCol.className = 'col-md-4 mb-3';
                        satisfactoryCol.innerHTML = `
                            <div class="subject-item">
                                <div class="form-check">
                                    <input class="form-check-input subject-checkbox" type="checkbox" 
                                        value="${subject}" id="satisfactory_${index}" name="satisfactory_subjects[]">
                                    <label class="form-check-label" for="satisfactory_${index}">
                                        ${subject}
                                    </label>
                                </div>
                                <div class="ms-4 mt-2 subject-details d-none">
                                    <div class="mb-2">
                                        <label class="form-label small">Количество тем с оценкой "3":</label>
                                        <input type="number" class="form-control form-control-sm" 
                                            name="satisfactory_topics_count_${subject.replace(/\s+/g, '_')}" min="1" value="1">
                                    </div>
                                </div>
                            </div>
                        `;
                        satisfactorySubjectsContainer.appendChild(satisfactoryCol);
                    }
                });
                
                // Добавляем обработчики для чекбоксов предметов
                addSubjectCheckboxHandlers();
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить список предметов', 'error');
            });
    }
    
    // Функция добавления обработчиков для чекбоксов предметов
    function addSubjectCheckboxHandlers() {
        const subjectCheckboxes = document.querySelectorAll('.subject-checkbox');
        
        subjectCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const subjectDetails = this.closest('.subject-item').querySelector('.subject-details');
                if (this.checked) {
                    subjectDetails.classList.remove('d-none');
                } else {
                    subjectDetails.classList.add('d-none');
                }
            });
        });
    }
    
    // Функция генерации формы для графика консультаций
    function generateConsultationsScheduleForm() {
        const consultationsScheduleSection = document.getElementById('consultationsScheduleSection');
        consultationsScheduleSection.innerHTML = '';
        
        // Получаем выбранные предметы с задолженностями
        const failedSubjects = [];
        document.querySelectorAll('input[name="failed_subjects[]"]:checked').forEach(checkbox => {
            const subjectName = checkbox.value;
            const topicsCountInput = document.querySelector(`input[name="failed_topics_count_${subjectName.replace(/\s+/g, '_')}"]`);
            const topicsCount = topicsCountInput ? parseInt(topicsCountInput.value) : 1;
            
            failedSubjects.push({
                name: subjectName,
                topicsCount: topicsCount
            });
        });
        
        // Получаем выбранные предметы с удовлетворительными оценками
        const satisfactorySubjects = [];
        document.querySelectorAll('input[name="satisfactory_subjects[]"]:checked').forEach(checkbox => {
            const subjectName = checkbox.value;
            const topicsCountInput = document.querySelector(`input[name="satisfactory_topics_count_${subjectName.replace(/\s+/g, '_')}"]`);
            const topicsCount = topicsCountInput ? parseInt(topicsCountInput.value) : 1;
            
            satisfactorySubjects.push({
                name: subjectName,
                topicsCount: topicsCount
            });
        });
        
        // Если нет выбранных предметов, показываем сообщение
        if (failedSubjects.length === 0 && satisfactorySubjects.length === 0) {
            consultationsScheduleSection.innerHTML = '<div class="alert alert-warning">Нет выбранных предметов для графика консультаций</div>';
            return;
        }
        
        // Создаем разделы для каждого предмета с задолженностями
        failedSubjects.forEach(subject => {
            const subjectSection = document.createElement('div');
            subjectSection.className = 'card mb-3';
            
            subjectSection.innerHTML = `
                <div class="card-header bg-danger text-white">
                    <h5 class="mb-0">${subject.name} - Задолженность</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        ${generateTopicConsultationsInputs(subject.name, 'failed', subject.topicsCount)}
                    </div>
                </div>
            `;
            
            consultationsScheduleSection.appendChild(subjectSection);
        });
        
        // Создаем разделы для каждого предмета с удовлетворительными оценками
        satisfactorySubjects.forEach(subject => {
            const subjectSection = document.createElement('div');
            subjectSection.className = 'card mb-3';
            
            subjectSection.innerHTML = `
                <div class="card-header bg-warning">
                    <h5 class="mb-0">${subject.name} - Удовлетворительно</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        ${generateTopicConsultationsInputs(subject.name, 'satisfactory', subject.topicsCount)}
                    </div>
                </div>
            `;
            
            consultationsScheduleSection.appendChild(subjectSection);
        });
        
        // Загружаем расписание звонков для выбора времени
        loadScheduleTimes();
    }
    
    // Функция генерации полей ввода для консультаций по темам
    function generateTopicConsultationsInputs(subjectName, type, topicsCount) {
        let html = '';
        
        for (let i = 1; i <= topicsCount; i++) {
            const subjectKey = subjectName.replace(/\s+/g, '_');
            const namePrefix = `${type}_consultations_${subjectKey}_topic_${i}`;
            
            html += `
                <div class="col-12 mb-3">
                    <h6>Тема ${i}</h6>
                    <div class="row g-2">
                        <div class="col-md-6">
                            <label class="form-label">Название темы/периода</label>
                            <input type="text" class="form-control" name="${namePrefix}_name" placeholder="Название темы">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Дата консультации</label>
                            <input type="date" class="form-control" name="${namePrefix}_date">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Урок (время)</label>
                            <select class="form-control lesson-select" name="${namePrefix}_lesson">
                                <option value="">Выберите урок</option>
                                <!-- Варианты будут загружены через JS -->
                            </select>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return html;
    }
    
    // Функция загрузки расписания звонков
    function loadScheduleTimes() {
        fetch('/api/get_schedule_times')
            .then(response => response.json())
            .then(times => {
                const lessonSelects = document.querySelectorAll('.lesson-select');
                
                lessonSelects.forEach(select => {
                    // Добавляем первую пустую опцию
                    select.innerHTML = '<option value="">Выберите урок</option>';
                    
                    // Добавляем варианты с уроками
                    times.forEach(time => {
                        const option = document.createElement('option');
                        option.value = time.id;
                        option.textContent = `${time.name} (${time.start} - ${time.end})`;
                        select.appendChild(option);
                    });
                });
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить расписание звонков', 'error');
            });
    }
    
    // Функция для отображения toast-уведомлений
    function showToast(title, message, type) {
        const toast = document.getElementById('toast');
        const toastTitle = document.getElementById('toastTitle');
        const toastMessage = document.getElementById('toastMessage');
        
        toastTitle.textContent = title;
        toastMessage.textContent = message;
        
        // Устанавливаем класс в зависимости от типа уведомления
        toast.classList.remove('bg-success', 'bg-danger');
        
        if (type === 'success') {
            toast.classList.add('bg-success', 'text-white');
        } else if (type === 'error') {
            toast.classList.add('bg-danger', 'text-white');
        }
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
});