/**
 * Общие функции для всех страниц приложения
 */

// Функция для отображения toast-уведомлений
function showToast(title, message, type) {
    const toast = document.getElementById('toast');
    const toastTitle = document.getElementById('toastTitle');
    const toastMessage = document.getElementById('toastMessage');
    
    if (!toast || !toastTitle || !toastMessage) {
        console.error('Toast elements not found');
        return;
    }
    
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

// Функция для форматирования даты
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

// Функция для проверки заполнения обязательных полей формы
function validateForm(form, requiredFields) {
    let isValid = true;
    
    requiredFields.forEach(fieldName => {
        const field = form.querySelector(`[name="${fieldName}"]`);
        
        if (!field || !field.value.trim()) {
            isValid = false;
            
            // Добавляем класс для невалидного поля
            if (field) {
                field.classList.add('is-invalid');
                
                // Добавляем обработчик для удаления класса при изменении поля
                field.addEventListener('input', function() {
                    if (this.value.trim()) {
                        this.classList.remove('is-invalid');
                    }
                });
            }
        }
    });
    
    return isValid;
}

// Функция для поиска по таблице
function searchTable(tableId, searchInput) {
    const searchText = searchInput.value.toLowerCase();
    const table = document.getElementById(tableId);
    
    if (!table) {
        console.error(`Table with id ${tableId} not found`);
        return;
    }
    
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        let found = false;
        const cells = row.querySelectorAll('td');
        
        cells.forEach(cell => {
            if (cell.textContent.toLowerCase().includes(searchText)) {
                found = true;
            }
        });
        
        row.style.display = found ? '' : 'none';
    });
}

// Функция для сортировки таблицы по клику на заголовок
function makeSortable(tableId) {
    const table = document.getElementById(tableId);
    
    if (!table) {
        console.error(`Table with id ${tableId} not found`);
        return;
    }
    
    const headers = table.querySelectorAll('th[data-sortable]');
    
    headers.forEach(header => {
        header.classList.add('cursor-pointer');
        
        header.addEventListener('click', function() {
            const columnIndex = Array.from(this.parentElement.children).indexOf(this);
            const isNumeric = this.dataset.type === 'number';
            const ascending = this.classList.contains('sort-asc');
            
            // Сбрасываем классы сортировки для всех заголовков
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            // Устанавливаем класс сортировки для текущего заголовка
            this.classList.add(ascending ? 'sort-desc' : 'sort-asc');
            
            // Сортируем строки
            const rows = Array.from(table.querySelectorAll('tbody tr'));
            
            rows.sort((a, b) => {
                const aValue = a.children[columnIndex].textContent.trim();
                const bValue = b.children[columnIndex].textContent.trim();
                
                if (isNumeric) {
                    return ascending ? 
                        parseFloat(aValue) - parseFloat(bValue) : 
                        parseFloat(bValue) - parseFloat(aValue);
                } else {
                    return ascending ? 
                        aValue.localeCompare(bValue) : 
                        bValue.localeCompare(aValue);
                }
            });
            
            // Добавляем отсортированные строки обратно в таблицу
            const tbody = table.querySelector('tbody');
            rows.forEach(row => {
                tbody.appendChild(row);
            });
        });
    });
}

// Функция для форматирования телефонного номера
function formatPhoneNumber(input) {
    let value = input.value.replace(/\D/g, '');
    
    if (value.length > 0) {
        if (value.length <= 3) {
            value = '+7(' + value;
        } else if (value.length <= 6) {
            value = '+7(' + value.substring(0, 3) + ')' + value.substring(3);
        } else if (value.length <= 8) {
            value = '+7(' + value.substring(0, 3) + ')' + value.substring(3, 6) + '-' + value.substring(6);
        } else {
            value = '+7(' + value.substring(0, 3) + ')' + value.substring(3, 6) + '-' + value.substring(6, 8) + '-' + value.substring(8, 10);
        }
    }
    
    input.value = value;
}

// Инициализация всплывающих подсказок Bootstrap
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});