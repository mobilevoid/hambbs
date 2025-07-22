(function(){
  function setupDraft(form){
    const key = form.dataset.key;
    if(!key) return;
    const title = form.querySelector('input[name="title"]');
    const body = form.querySelector('textarea[name="body"]');
    if(!body) return;
    try{
      const saved = localStorage.getItem(key);
      if(saved){
        const data = JSON.parse(saved);
        if(data.body && !body.value) body.value = data.body;
        if(title && data.title && !title.value) title.value = data.title;
        form.classList.add('draft-exists');
      }
    }catch(e){}
    const save = () => {
      const data = {
        title: title ? title.value : '',
        body: body.value
      };
      localStorage.setItem(key, JSON.stringify(data));
      form.classList.add('draft-exists');
    };
    body.addEventListener('input', save);
    if(title) title.addEventListener('input', save);
    form.addEventListener('submit', () => localStorage.removeItem(key));
  }

  function setupPreview(form){
    const btn = form.querySelector('.preview-btn');
    const area = form.querySelector('textarea[name="body"]');
    const box = form.querySelector('.preview');
    if(!btn || !area || !box) return;
    btn.addEventListener('click', async () => {
      if(!box.classList.contains('d-none')){
        box.classList.add('d-none');
        btn.textContent = 'Preview';
        return;
      }
      const resp = await fetch('/preview', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({text: area.value})
      });
      const data = await resp.json();
      box.innerHTML = data.html;
      box.classList.remove('d-none');
      btn.textContent = 'Hide Preview';
    });
  }

  function setupThreadSearch(){
    const input = document.getElementById('thread-search');
    if(!input) return;
    const items = document.querySelectorAll('#posts-list .post-item');
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase();
      items.forEach(it => {
        const text = it.innerText.toLowerCase();
        if(text.includes(q)) it.classList.remove('d-none');
        else it.classList.add('d-none');
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form.autosave').forEach(setupDraft);
    document.querySelectorAll('form').forEach(setupPreview);
    setupThreadSearch();
  });
})();
