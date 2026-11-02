// Scout Sandou2 Finance JavaScript
document.addEventListener('DOMContentLoaded', function () {

    // EDIT MODAL HANDLER
    const editModal = document.getElementById('editModal');
    if (editModal) {
        editModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (!button) return;

            const id = button.getAttribute('data-id');
            const type = button.getAttribute('data-type');
            const amount = button.getAttribute('data-amount');
            const currency = button.getAttribute('data-currency');
            const party = button.getAttribute('data-party');
            const category = button.getAttribute('data-category');
            const notes = button.getAttribute('data-notes') || '';
            const date = button.getAttribute('data-date');

            // Form action target
            const editForm = document.getElementById('editForm');
            editForm.action = `/transaction/edit/${id}`;

            // Populate form inputs
            if (type === 'income') {
                document.getElementById('editTypeIncome').checked = true;
                document.getElementById('editPartyLabel').innerHTML = '<i class="fa-solid fa-user me-1 text-success"></i> ' + window.scoutTranslate('From Who? (من مين / مصدر المال)');
            } else {
                document.getElementById('editTypeExpense').checked = true;
                document.getElementById('editPartyLabel').innerHTML = '<i class="fa-solid fa-receipt me-1 text-danger"></i> ' + window.scoutTranslate('For What? (السبب / لشو اندفعت)');
            }

            document.getElementById('editAmount').value = amount;

            if (currency === 'USD') {
                document.getElementById('editCurrencyUsd').checked = true;
            } else {
                document.getElementById('editCurrencyLbp').checked = true;
            }

            document.getElementById('editParty').value = party;
            document.getElementById('editCategory').value = category;
            document.getElementById('editNotes').value = notes;
            document.getElementById('editDate').value = date;
        });

        // Type switcher listener inside Edit Modal
        const editTypeIncome = document.getElementById('editTypeIncome');
        const editTypeExpense = document.getElementById('editTypeExpense');
        const editPartyLabel = document.getElementById('editPartyLabel');

        if (editTypeIncome && editTypeExpense && editPartyLabel) {
            editTypeIncome.addEventListener('change', function () {
                if (this.checked) {
                    editPartyLabel.innerHTML = '<i class="fa-solid fa-user me-1 text-success"></i> ' + window.scoutTranslate('From Who? (من مين / مصدر المال)');
                }
            });
            editTypeExpense.addEventListener('change', function () {
                if (this.checked) {
                    editPartyLabel.innerHTML = '<i class="fa-solid fa-receipt me-1 text-danger"></i> ' + window.scoutTranslate('For What? (السبب / لشو اندفعت)');
                }
            });
        }
    }

    // DELETE MODAL HANDLER
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (!button) return;

            const id = button.getAttribute('data-id');
            const party = button.getAttribute('data-party');
            const amount = button.getAttribute('data-amount');

            const deleteForm = document.getElementById('deleteForm');
            deleteForm.action = `/transaction/delete/${id}`;

            document.getElementById('delPartyName').textContent = party;
            document.getElementById('delAmount').textContent = amount;
        });
    }

    // AUTO DISMISS ALERTS
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            try {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            } catch (e) {}
        }, 5000);
    });

});
