// static/js/notification_form_simple.js

document.addEventListener('DOMContentLoaded', function() {
    // Отладочные функции
    function debug(message, data = null) {
        console.log('%c[DEBUG] ' + message, 'background: #f0f0f0; color: #333');
        if (data) {
            console.log(data);
        }
    }

    // Получаем параметры из URL
    const urlParams = new URLSearchParams(window.location.search);
    const studentId = urlParams.get('student_id');
    const failedSubjectsParam = urlParams.get('failed_subjects');
    const satisfactorySubjectsParam = urlParams.get('satisfactory_subjects');
    
    debug('URL параметры:', { 
        studentId, 
        failedSubjectsParam, 
        satisfactorySubjectsParam 
    });

    // Элементы формы
    const form = document.getElementById('notificationForm');
    const classSelect = document.getElementById('classSelect');
    const studentSelect = document.getElementById('studentSelect');
    const needConsultationsCheckbox = document.getElementById('needConsultationsSchedule');
    const needDeadlineCheckbox = document.getElementById('needDeadline');
    const deadlineSection = document.getElementById('deadlineSection');
    const deadlineCheckboxContainer = document.getElementById('deadlineCheckboxContainer');
    const consultationsScheduleSection = document.getElementById('consultationsScheduleSection');
    
    // Загружаем список классов
    loadClasses().then(() => {
        // После загрузки классов, если есть ID студента, выбираем его
        if (studentId) {
            debug('Получен ID ученика, загружаем данные', studentId);
            fillFormWithStudentData(studentId);
        }
    });
    
    // Функция для заполнения формы данными ученика
    function fillFormWithStudentData(studentId) {
        fetch(`/api/get_student/${studentId}`)
            .then(response => response.json())
            .then(data => {
                debug('Ответ API get_student:', data);
                if (data.success) {
                    const student = data.student;
                    
                    // Выбираем класс ученика
                    if (classSelect && student.class_name) {
                        debug('Выбираем класс:', student.class_name);
                        classSelect.value = student.class_name;
                        
                        // Вызываем событие change для загрузки учеников
                        classSelect.dispatchEvent(new Event('change'));
                        
                        // Ждем загрузки списка учеников
                        setTimeout(() => {
                            // Выбираем ученика
                            if (studentSelect) {
                                debug('Опции в списке учеников:', Array.from(studentSelect.options).map(o => ({ value: o.value, text: o.text })));
                                studentSelect.value = studentId;
                                debug('Ученик выбран:', studentSelect.value);
                                
                                // Вызываем событие change для загрузки предметов
                                studentSelect.dispatchEvent(new Event('change'));
                                
                                // После загрузки предметов, выбираем предметы
                                setTimeout(() => {
                                    debug('Вызываем выбор предметов');
                                    selectSubjects(failedSubjectsParam, satisfactorySubjectsParam);
                                }, 1000); // Даем время на загрузку предметов
                            } else {
                                debug('Не найден элемент studentSelect');
                            }
                        }, 1000); // Даем время на загрузку учеников
                    }
                } else {
                    debug('Ошибка при получении данных ученика');
                    showToast('Ошибка', 'Не удалось загрузить данные ученика', 'error');
                }
            })
            .catch(error => {
                debug('Исключение при получении данных ученика:', error);
                showToast('Ошибка', 'Не удалось загрузить данные ученика', 'error');
            });
    }
    
    // Функция для выбора предметов
    function selectSubjects(failedSubjectsParam, satisfactorySubjectsParam) {
        debug('Выбор предметов с задолженностями и тройками');
        
        if (failedSubjectsParam) {
            const failedSubjects = decodeURIComponent(failedSubjectsParam).split(',');
            debug('Предметы с задолженностями:', failedSubjects);
            
            const failedCheckboxes = document.querySelectorAll('input[name="failed_subjects[]"]');
            debug('Найдено чекбоксов задолженностей:', failedCheckboxes.length);
            
            failedCheckboxes.forEach(checkbox => {
                debug('Проверяем чекбокс:', checkbox.value);
                if (failedSubjects.includes(checkbox.value)) {
                    debug('Выбираем чекбокс:', checkbox.value);
                    checkbox.checked = true;
                    // Если есть блок с деталями, показываем его
                    const subjectDetails = checkbox.closest('.subject-item').querySelector('.subject-details');
                    if (subjectDetails) {
                        debug('Показываем детали предмета');
                        subjectDetails.classList.remove('d-none');
                    }
                }
            });
        }
        
        if (satisfactorySubjectsParam) {
            const satisfactorySubjects = decodeURIComponent(satisfactorySubjectsParam).split(',');
            debug('Предметы с тройками:', satisfactorySubjects);
            
            const satisfactoryCheckboxes = document.querySelectorAll('input[name="satisfactory_subjects[]"]');
            debug('Найдено чекбоксов троек:', satisfactoryCheckboxes.length);
            
            satisfactoryCheckboxes.forEach(checkbox => {
                debug('Проверяем чекбокс:', checkbox.value);
                if (satisfactorySubjects.includes(checkbox.value)) {
                    debug('Выбираем чекбокс:', checkbox.value);
                    checkbox.checked = true;
                }
            });
        }
    }
    
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
        
        // Определяем, является ли класс "A" классом
        const isClassA = className.includes('А') || className.includes('A');
        
        // Показываем/скрываем блок указания крайнего срока для классов без литеры "А"
        if (isClassA) {
            deadlineCheckboxContainer.classList.add('d-none');
            needDeadlineCheckbox.checked = false;
            deadlineSection.classList.add('d-none');
        } else {
            deadlineCheckboxContainer.classList.remove('d-none');
        }
    });
    
    // Обработчик изменения выбора ученика - загружаем предметы
    studentSelect.addEventListener('change', function() {
        if (this.value) {
            const selectedOption = this.options[this.selectedIndex];
            const className = selectedOption.dataset.className || classSelect.value;
            
            if (className) {
                loadSubjectsByClass(className);
            }
        }
    });
    
    // Обработчик изменения чекбокса графика консультаций
    needConsultationsCheckbox.addEventListener('change', function() {
        if (this.checked) {
            consultationsScheduleSection.classList.remove('d-none');
            // Генерируем форму для графика консультаций
            generateConsultationsScheduleForm();
        } else {
            consultationsScheduleSection.classList.add('d-none');
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
    // Замените существующий обработчик отправки формы в notification_form_simple.js
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Проверяем обязательные поля
        const classValue = classSelect.value;
        const student = studentSelect.value;
        
        if (!classValue || !student) {
            showToast('Ошибка', 'Выберите класс и ученика', 'error');
            return;
        }
        
        // Проверка выбора предметов
        const failedSubjects = document.querySelectorAll('input[name="failed_subjects[]"]:checked');
        const satisfactorySubjects = document.querySelectorAll('input[name="satisfactory_subjects[]"]:checked');
        
        // Проверяем, есть ли хотя бы один предмет (либо задолженность, либо тройка)
        if (failedSubjects.length === 0 && satisfactorySubjects.length === 0) {
            showToast('Ошибка', 'Выберите хотя бы один предмет с задолженностью или тройкой', 'error');
            return;
        }
        
        // Собираем данные формы
        const formData = new FormData(form);
        
        // Добавляем тип периода (для совместимости с бэкендом)
        formData.append('period_type', 'module');
        
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
    
    // Функция загрузки списка классов
    function loadClasses() {
        return fetch('/api/get_unique_classes')
            .then(response => response.json())
            .then(classes => {
                classSelect.innerHTML = '<option value="">Выберите класс</option>';
                
                classes.forEach(className => {
                    const option = document.createElement('option');
                    option.value = className;
                    option.textContent = className;
                    classSelect.appendChild(option);
                });
                
                debug('Загружено классов:', classes.length);
                return classes;
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить список классов', 'error');
                debug('Ошибка при загрузке классов:', error);
                return [];
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
                
                debug('Загружено учеников:', students.length);
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить список учеников', 'error');
                debug('Ошибка при загрузке учеников:', error);
            });
    }
    
    // Функция загрузки предметов по классу
    function loadSubjectsByClass(className) {
        // Извлекаем номер класса (параллель)
        const gradeMatch = className.match(/^(\d+)/);
        if (!gradeMatch || !gradeMatch[1]) {
            showToast('Ошибка', 'Не удалось определить параллель класса', 'error');
            debug('Не удалось определить параллель класса:', className);
            return;
        }
        
        const grade = gradeMatch[1];
        
        fetch(`/api/get_subjects_by_grade/${grade}`)
            .then(response => response.json())
            .then(subjects => {
                debug('Загружено предметов:', subjects.length);
                
                // Заполняем список предметов с академическими задолженностями
                const failedSubjectsContainer = document.getElementById('failedSubjectsContainer');
                failedSubjectsContainer.innerHTML = '';
                
                // Заполняем список предметов с удовлетворительными оценками
                const satisfactorySubjectsContainer = document.getElementById('satisfactorySubjectsContainer');
                satisfactorySubjectsContainer.innerHTML = '';
                
                // Определяем, является ли класс "A" классом
                const isClassA = className.includes('А') || className.includes('A');
                
                // Показываем/скрываем секцию удовлетворительных оценок в зависимости от класса
                const satisfactorySubjectsSection = document.getElementById('satisfactorySubjectsSection');
                if (isClassA) {
                    satisfactorySubjectsSection.classList.add('d-none');
                } else {
                    satisfactorySubjectsSection.classList.remove('d-none');
                }
                
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
                            </div>
                        `;
                        satisfactorySubjectsContainer.appendChild(satisfactoryCol);
                    }
                });
                
                // Добавляем обработчики для чекбоксов предметов
                addSubjectCheckboxHandlers();
                
                // Если есть параметры предметов в URL, выбираем их после загрузки
                if (failedSubjectsParam || satisfactorySubjectsParam) {
                    debug('Повторная попытка выбора предметов после загрузки');
                    selectSubjects(failedSubjectsParam, satisfactorySubjectsParam);
                }
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить список предметов', 'error');
                debug('Ошибка при загрузке предметов:', error);
            });
    }
    
    // Функция добавления обработчиков для чекбоксов предметов
    function addSubjectCheckboxHandlers() {
        const subjectCheckboxes = document.querySelectorAll('.subject-checkbox');
        
        subjectCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const subjectDetails = this.closest('.subject-item').querySelector('.subject-details');
                if (subjectDetails) {
                    if (this.checked) {
                        subjectDetails.classList.remove('d-none');
                    } else {
                        subjectDetails.classList.add('d-none');
                    }
                }
            });
        });
    }
    
    // Функция генерации формы для графика консультаций
    function generateConsultationsScheduleForm() {
        const consultationsScheduleSection = document.getElementById('consultationsScheduleSection');
        
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
        
        // Если нет выбранных предметов, показываем сообщение
        if (failedSubjects.length === 0) {
            consultationsScheduleSection.innerHTML = '<div class="alert alert-warning">Нет выбранных предметов для графика консультаций</div>';
            return;
        }
        
        // Контейнер для формы консультаций
        const formContainer = document.createElement('div');
        
        // Создаем разделы для каждого предмета с задолженностями
        failedSubjects.forEach(subject => {
            const subjectSection = document.createElement('div');
            subjectSection.className = 'card mb-3';
            subjectSection.dataset.subject = subject.name;
            
            // Заголовок секции предмета с кнопкой добавления консультации
            const header = document.createElement('div');
            header.className = 'card-header bg-danger text-white d-flex justify-content-between align-items-center';
            header.innerHTML = `
                <h5 class="mb-0">${subject.name} - Задолженность</h5>
                <button type="button" class="btn btn-light btn-sm add-consultation-btn" data-subject="${subject.name}">
                    <i class="bi bi-plus-circle"></i> Добавить консультацию
                </button>
            `;
            subjectSection.appendChild(header);
            
            // Тело карточки с темами
            const body = document.createElement('div');
            body.className = 'card-body';
            
            // Контейнер для тем
            const topicsContainer = document.createElement('div');
            topicsContainer.className = 'topics-container';
            topicsContainer.id = `topics-container-${subject.name.replace(/\s+/g, '_')}`;
            
            // Создаем разделы для каждой темы
            for (let i = 1; i <= subject.topicsCount; i++) {
                const topicSection = createTopicSection(subject.name, i);
                topicsContainer.appendChild(topicSection);
            }
            
            body.appendChild(topicsContainer);
            subjectSection.appendChild(body);
            formContainer.appendChild(subjectSection);
        });
        
        // Обновляем содержимое секции консультаций
        consultationsScheduleSection.innerHTML = '';
        consultationsScheduleSection.appendChild(formContainer);
        
        // Добавляем обработчики для кнопок добавления консультаций
        document.querySelectorAll('.add-consultation-btn').forEach(button => {
            button.addEventListener('click', function() {
                const subjectName = this.dataset.subject;
                const topicsContainer = document.querySelector(`#topics-container-${subjectName.replace(/\s+/g, '_')}`);
                
                // Находим последний номер темы и увеличиваем его на 1
                const existingTopics = topicsContainer.querySelectorAll('.topic-section');
                const nextTopicNumber = existingTopics.length + 1;
                
                // Создаем новый раздел для темы
                const newTopicSection = createTopicSection(subjectName, nextTopicNumber);
                topicsContainer.appendChild(newTopicSection);
                
                // Обновляем счетчик тем в форме
                const topicsCountInput = document.querySelector(`input[name="failed_topics_count_${subjectName.replace(/\s+/g, '_')}"]`);
                if (topicsCountInput) {
                    topicsCountInput.value = nextTopicNumber;
                }
                
                // Загружаем расписание звонков для новой консультации
                loadScheduleTimesForTopic(subjectName, nextTopicNumber);
            });
        });
        
        // Загружаем расписание звонков для всех тем
        loadScheduleTimes();
    }
    
    // Функция создания раздела для темы
    function createTopicSection(subjectName, topicNumber) {
        const topicSection = document.createElement('div');
        topicSection.className = 'topic-section mb-4';
        topicSection.dataset.topicNumber = topicNumber;
        
        // Заголовок темы с возможностью удаления
        const topicHeader = document.createElement('div');
        topicHeader.className = 'd-flex justify-content-between align-items-center mb-2';
        topicHeader.innerHTML = `
            <h6>Консультация ${topicNumber}</h6>
            <button type="button" class="btn btn-sm btn-outline-danger remove-topic-btn" 
                data-subject="${subjectName}" data-topic="${topicNumber}">
                <i class="bi bi-trash"></i>
            </button>
        `;
        
        // Форма для консультации
        const consultationForm = document.createElement('div');
        consultationForm.className = 'row g-2';
        consultationForm.innerHTML = `
            <div class="col-md-6">
                <label class="form-label">Тема (необязательно)</label>
                <input type="text" class="form-control" 
                    name="failed_consultations_${subjectName.replace(/\s+/g, '_')}_topic_${topicNumber}_name" 
                    placeholder="Название темы (не обязательно)">
            </div>
            <div class="col-md-3">
                <label class="form-label">Дата консультации</label>
                <input type="date" class="form-control" 
                    name="failed_consultations_${subjectName.replace(/\s+/g, '_')}_topic_${topicNumber}_date" required>
            </div>
            <div class="col-md-3">
                <label class="form-label">Урок (время)</label>
                <select class="form-control lesson-select" 
                    name="failed_consultations_${subjectName.replace(/\s+/g, '_')}_topic_${topicNumber}_lesson" required>
                    <option value="">Выберите урок</option>
                    <!-- Варианты будут загружены через JS -->
                </select>
            </div>
        `;
        
        topicSection.appendChild(topicHeader);
        topicSection.appendChild(consultationForm);
        
        // Добавляем обработчик для кнопки удаления темы
        setTimeout(() => {
            const removeButton = topicSection.querySelector('.remove-topic-btn');
            if (removeButton) {
                removeButton.addEventListener('click', function() {
                    // Если это единственная тема, не даем удалить
                    const topicsContainer = topicSection.closest('.topics-container');
                    if (topicsContainer.querySelectorAll('.topic-section').length <= 1) {
                        showToast('Внимание', 'Должна быть хотя бы одна консультация', 'error');
                        return;
                    }
                    
                    // Удаляем секцию темы
                    topicSection.remove();
                    
                    // Перенумеровываем оставшиеся темы
                    renumberTopics(topicsContainer, subjectName);
                });
            }
        }, 0);
        
        return topicSection;
    }
    
    // Функция для перенумерации тем после удаления
    function renumberTopics(topicsContainer, subjectName) {
        const topics = topicsContainer.querySelectorAll('.topic-section');
        
        topics.forEach((topic, index) => {
            const newNumber = index + 1;
            const oldNumber = parseInt(topic.dataset.topicNumber);
            
            // Обновляем заголовок
            const header = topic.querySelector('h6');
            if (header) {
                header.textContent = `Консультация ${newNumber}`;
            }
            
            // Обновляем data-атрибут
            topic.dataset.topicNumber = newNumber;
            
            // Обновляем атрибуты кнопки удаления
            const removeButton = topic.querySelector('.remove-topic-btn');
            if (removeButton) {
                removeButton.dataset.topic = newNumber;
            }
            
            // Обновляем имена полей
            if (oldNumber !== newNumber) {
                const inputs = topic.querySelectorAll('input, select');
                inputs.forEach(input => {
                    const oldName = input.name;
                    const newName = oldName.replace(`_topic_${oldNumber}_`, `_topic_${newNumber}_`);
                    input.name = newName;
                });
            }
        });
        
        // Обновляем счетчик тем в форме
        const topicsCountInput = document.querySelector(`input[name="failed_topics_count_${subjectName.replace(/\s+/g, '_')}"]`);
        if (topicsCountInput) {
            topicsCountInput.value = topics.length;
        }
    }
    
    // Функция загрузки расписания звонков для всех тем
    function loadScheduleTimes() {
        fetch('/api/get_schedule_times')
            .then(response => response.json())
            .then(times => {
                window.scheduleTimes = times; // Сохраняем для использования в других функциях
                
                const lessonSelects = document.querySelectorAll('.lesson-select');
                
                lessonSelects.forEach(select => {
                    populateLessonSelect(select, times);
                });
            })
            .catch(error => {
                showToast('Ошибка', 'Не удалось загрузить расписание звонков', 'error');
                debug('Ошибка при загрузке расписания звонков:', error);
            });
    }
    
    // Функция загрузки расписания звонков для конкретной темы
    function loadScheduleTimesForTopic(subjectName, topicNumber) {
        if (window.scheduleTimes) {
            const select = document.querySelector(`select[name="failed_consultations_${subjectName.replace(/\s+/g, '_')}_topic_${topicNumber}_lesson"]`);
            if (select) {
                populateLessonSelect(select, window.scheduleTimes);
            }
        } else {
            loadScheduleTimes();
        }
    }
    
    // Функция заполнения селекта с расписанием звонков
    function populateLessonSelect(select, times) {
        // Добавляем первую пустую опцию
        select.innerHTML = '<option value="">Выберите урок</option>';
        
        // Добавляем варианты с уроками
        times.forEach(time => {
            const option = document.createElement('option');
            option.value = time.id;
            option.textContent = `${time.name} (${time.start} - ${time.end})`;
            select.appendChild(option);
        });
    }
});