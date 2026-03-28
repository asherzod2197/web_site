// ============================================
// Веб-мониторинг — JavaScript
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Автоскрытие алертов
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });

    // Подтверждение удаления
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (!confirm('Вы уверены, что хотите удалить это отслеживание?')) {
                e.preventDefault();
            }
        });
    });

    // Toggle для чекбоксов — синхронизация скрытого поля
    document.querySelectorAll('.toggle input[type="checkbox"]').forEach(checkbox => {
        const hiddenInput = checkbox.closest('form')?.querySelector(
            `input[type="hidden"][name="${checkbox.name}"]`
        );
        if (hiddenInput) {
            checkbox.addEventListener('change', () => {
                hiddenInput.disabled = checkbox.checked;
            });
        }
    });

    // Анимация строк таблицы при загрузке
    const tableRows = document.querySelectorAll('.table tbody tr');
    tableRows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(10px)';
        setTimeout(() => {
            row.style.transition = 'all 0.3s ease';
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, 50 * index);
    });

    // Фильтр по отслеживанию в журнале
    const logFilter = document.getElementById('log-filter');
    if (logFilter) {
        logFilter.addEventListener('change', () => {
            const trackingId = logFilter.value;
            const url = new URL(window.location.href);
            if (trackingId) {
                url.searchParams.set('tracking_id', trackingId);
            } else {
                url.searchParams.delete('tracking_id');
            }
            url.searchParams.set('page', '1');
            window.location.href = url.toString();
        });
    }
});
