document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('password');
  
    // Allow login on Enter key press
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        document.querySelector('form').submit();
      }
    });
  
    // Toggle password visibility
    const toggle = document.getElementById('togglePassword');
    if (toggle && passwordInput) {
      toggle.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        toggle.classList.toggle('active');
      });
    }
  });
  