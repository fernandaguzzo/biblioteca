document.addEventListener('DOMContentLoaded', function() {
    // Modal de empréstimo
    const modal = document.getElementById('emprestimo-modal');
    const emprestarBtns = document.querySelectorAll('.emprestar-btn');
    const closeBtn = document.querySelector('.close');
    const livroIdInput = document.getElementById('livro-id');
    const emprestimoForm = document.getElementById('emprestimo-form');
    
    emprestarBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const livroCard = this.closest('.book-card');
            const livroId = livroCard.getAttribute('data-id');
            livroIdInput.value = livroId;
            modal.style.display = 'block';
        });
    });
    
    closeBtn.addEventListener('click', function() {
        modal.style.display = 'none';
    });
    
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Formulário de empréstimo
    emprestimoForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const livroId = livroIdInput.value;
        const usuario = document.getElementById('usuario').value;
        
        fetch('/emprestar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                livro_id: livroId,
                usuario: usuario
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Livro emprestado com sucesso!');
                modal.style.display = 'none';
                window.location.reload();
            } else {
                alert('Erro ao emprestar livro. Tente novamente.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Erro ao processar a solicitação.');
        });
    });
    
    // Filtro de livros
    const filterSelect = document.getElementById('disponivel');
    if (filterSelect) {
        filterSelect.addEventListener('change', function() {
            const value = this.value;
            const bookItems = document.querySelectorAll('.book-item');
            
            bookItems.forEach(item => {
                const isAvailable = item.getAttribute('data-available') === 'true';
                
                if (value === 'all') {
                    item.style.display = 'block';
                } else if (value === 'available' && isAvailable) {
                    item.style.display = 'block';
                } else if (value === 'unavailable' && !isAvailable) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
});

// Atualizar a parte do empréstimo
emprestimoForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const livroId = livroIdInput.value;
    
    fetch('/emprestar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            livro_id: livroId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`Livro emprestado com sucesso! Data de devolução: ${data.devolucao}`);
            modal.style.display = 'none';
            window.location.reload();
        } else {
            alert(data.message || 'Erro ao emprestar livro. Tente novamente.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erro ao processar a solicitação.');
    });
});
