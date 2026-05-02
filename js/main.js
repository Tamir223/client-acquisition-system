document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('lead-form');
    const messageEl = document.getElementById('form-message');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;

        submitBtn.textContent = 'Sending...';
        submitBtn.disabled = true;
        messageEl.textContent = '';
        messageEl.className = 'form-message';

        const payload = {
            first_name: form.first_name.value.trim(),
            last_name:  form.last_name.value.trim(),
            email:      form.email.value.trim(),
            company:    form.company.value.trim(),
            niche:      form.niche.value.trim(),
        };

        try {
            const res = await fetch('/api/lead', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await res.json();

            if (res.ok) {
                messageEl.textContent = "Got it! We'll be in touch within 24 hours.";
                messageEl.classList.add('success');
                form.reset();
            } else {
                throw new Error(data.error || 'Something went wrong.');
            }
        } catch (err) {
            messageEl.textContent = err.message || 'Something went wrong. Please try again.';
            messageEl.classList.add('error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    });
});
