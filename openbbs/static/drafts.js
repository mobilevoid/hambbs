(function(){
  function setup(form) {
    const key = form.dataset.key;
    if (!key) return;
    const title = form.querySelector('input[name="title"]');
    const body = form.querySelector('textarea[name="body"]');
    if (!body) return;
    try {
      const saved = localStorage.getItem(key);
      if (saved) {
        const data = JSON.parse(saved);
        if (data.body && !body.value) body.value = data.body;
        if (title && data.title && !title.value) title.value = data.title;
        form.classList.add('draft-exists');
      }
    } catch(e) {}
    const save = () => {
      const data = {
        title: title ? title.value : '',
        body: body.value
      };
      localStorage.setItem(key, JSON.stringify(data));
      form.classList.add('draft-exists');
    };
    body.addEventListener('input', save);
    if (title) title.addEventListener('input', save);
    form.addEventListener('submit', () => localStorage.removeItem(key));
  }
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form.autosave').forEach(setup);
  });
})();
