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
    const warn = (e) => {
      if(form.classList.contains('draft-exists')){
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', warn);
    form.addEventListener('submit', () => {
      localStorage.removeItem(key);
      window.removeEventListener('beforeunload', warn);
    });
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
    const originals = new Map();
    items.forEach(it => originals.set(it, it.innerHTML));
    input.addEventListener('input', () => {
      const q = input.value.toLowerCase();
      items.forEach(it => {
        it.innerHTML = originals.get(it);
        const text = it.innerText.toLowerCase();
        if(!q){
          it.classList.remove('d-none');
          return;
        }
        if(text.includes(q)){
          it.classList.remove('d-none');
          const regex = new RegExp('('+q.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')+')', 'gi');
          it.innerHTML = it.innerHTML.replace(regex, '<mark>$1</mark>');
        }else{
          it.classList.add('d-none');
        }
      });
    });
  }

  function setupShortcuts(){
    document.addEventListener('keydown', (e) => {
      if(e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      const key = e.key.toLowerCase();
      if(key === 'n'){
        const el = document.getElementById('new-topic-title');
        if(el){
          e.preventDefault();
          el.focus();
        }
      } else if(key === 'e'){
        const edit = document.querySelector('.shortcut-edit');
        if(edit){
          e.preventDefault();
          edit.click();
        }
      } else if(key === 'f'){
        const flag = document.querySelector('.shortcut-flag');
        if(flag){
          e.preventDefault();
          flag.submit();
        }
      } else if(key === '/' || key === 's'){
        const search = document.getElementById('global-search');
        if(search){
          e.preventDefault();
          search.focus();
        }
      }
    });
  }

  function setupWarnForms(){
    document.querySelectorAll('.warn-form').forEach(form => {
      form.addEventListener('submit', e => {
        const input = form.querySelector('input[name="text"]');
        if(!input) return;
        const val = prompt('Enter warning note:');
        if(!val){
          e.preventDefault();
          return;
        }
        input.value = val;
      });
    });
  }

  function setupDeleteForms(){
    document.querySelectorAll('.delete-form').forEach(form => {
      form.addEventListener('submit', e => {
        const input = form.querySelector('input[name="reason"]');
        if(input){
          const val = prompt('Reason for deletion (optional):');
          input.value = val || '';
        }
      });
    });
  }

  function setupSearchSuggest(){
    const box = document.getElementById('global-search');
    const list = document.getElementById('search-list');
    if(!box || !list) return;
    let ctrl;
    box.addEventListener('input', () => {
      const q = box.value.trim();
      if(ctrl) ctrl.abort();
      if(!q){ list.innerHTML=''; return; }
      ctrl = new AbortController();
      fetch('/suggest?q='+encodeURIComponent(q), {signal: ctrl.signal})
        .then(r => r.json())
        .then(data => {
          list.innerHTML = data.results.map(r => `<option value="${r.title}">`).join('');
        }).catch(()=>{});
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form.autosave').forEach(setupDraft);
    document.querySelectorAll('form').forEach(setupPreview);
    setupThreadSearch();
    setupShortcuts();
    setupWarnForms();
    setupDeleteForms();
    setupSearchSuggest();
  });
})();
