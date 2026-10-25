import { CATEGORIES, TYPES, SEVERITIES, STATUSES, FINDING_STATUSES, createProject, activeItems, progress, openFindings, priority, syncTemplates, validateBackup, uid } from './model.js';

const KEY = 'prismaqa.projects.v1';
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const initial = () => {
  const p = createProject({ name: 'API de autenticação · exemplo', type: 'api', categories: Object.keys(CATEGORIES), description: 'Exemplo para explorar o fluxo de revisão. Crie sua própria avaliação para começar.', stack: 'NestJS · PostgreSQL', reference: '' });
  p.items[0].status = 'passed'; p.items[3].status = 'passed'; p.items[7].status = 'failed';
  p.findings.push({ id: uid(), title: 'Mensagens de erro expõem detalhes internos', category: 'vulnerabilities', severity: 'high', status: 'open', itemId: p.items[7].id, description: 'Exemplo fictício: uma resposta de erro expõe detalhes de implementação. Validar o tratamento de exceções e retornar mensagens seguras.', steps: 'Enviar uma entrada inválida ao endpoint de exemplo.', evidence: 'Registro ilustrativo, sem teste executado.', createdAt: new Date().toISOString() });
  return [p];
};

let projects;
try { const raw = localStorage.getItem(KEY); projects = raw ? validateBackup(JSON.parse(raw)) : initial(); }
catch { projects = initial(); }
let currentId = projects[0]?.id ?? null;
let tab = 'overview';
let editProjectId = null;
let editFindingId = null;
let checklistFilter = 'all';
let findingFilter = 'all';
let findingSearch = '';
let toastTimer;

function notify(message) { const node = $('#toast'); node.textContent = message; node.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => node.classList.remove('show'), 3100); }
function save() { try { localStorage.setItem(KEY, JSON.stringify({ format: 'prismaqa-v1', projects })); } catch { notify('Armazenamento cheio ou bloqueado. Exporte um backup dos dados.'); } }
function current() { return projects.find(p => p.id === currentId) ?? projects[0]; }
function touch(p) { p.updatedAt = new Date().toISOString(); save(); render(); }
function date(iso) { const d = new Date(iso); return Number.isNaN(d.valueOf()) ? 'Data indisponível' : new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(d); }
function validLink(value) { try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) ? u.href : null; } catch { return null; } }
function show(dialog) { dialog.showModal(); dialog.querySelector('input:not([type=radio]):not([type=checkbox])')?.focus(); }
function categorySelectOptions(p) { return p.categories.map(c => `<option value="${c}">${CATEGORIES[c].label}</option>`).join(''); }
function empty(title, desc, action, label) { return `<div class="empty"><div class="empty-icon">✳</div><h3>${title}</h3><p>${desc}</p>${action ? `<button class="button button-soft" data-action="${action}">${label}</button>` : ''}</div>`; }

function renderSidebar(p) {
  $('#projectList').innerHTML = projects.map(project => `<button class="project-link ${project.id === p?.id ? 'active' : ''}" data-project="${esc(project.id)}"><span class="project-icon">${TYPES[project.type].icon}</span><span style="min-width:0"><span class="project-name">${esc(project.name)}</span><span class="project-kind">${TYPES[project.type].label} · ${progress(project).pct}% concluído</span></span></button>`).join('');
  $('#mobileProjects').innerHTML = projects.map(project => `<option value="${esc(project.id)}" ${project.id === p?.id ? 'selected' : ''}>${esc(project.name)}</option>`).join('');
}

function render() {
  const p = current();
  if (!p) {
    renderSidebar(null);
    $('#crumbTitle').textContent = 'Avaliação';
    $('#projectTitle').textContent = 'Seu espaço de QA começa aqui';
    $('#projectDescription').textContent = 'Crie uma avaliação para montar o checklist e registrar os resultados.';
    $('#projectTypeBadge').textContent = 'NOVO'; $('#projectDate').textContent = ''; $('#heroTags').innerHTML = '';
    $('#metricProgress').textContent = '0%'; $('#metricProgressDetail').textContent = '0 de 0 verificados'; $('#progressFill').style.width = '0%';
    $('#metricOpen').textContent = '0'; $('#metricOpenDetail').textContent = 'Nenhuma pendência'; $('#metricPriority').textContent = '—'; $('#metricPriorityDetail').textContent = 'Sem achados em aberto';
    $('#tabChecklistCount').textContent = '0'; $('#tabFindingsCount').textContent = '0';
    $('#editProjectBtn').hidden = true; $('#deleteProjectBtn').hidden = true; $('#addFindingTop').disabled = true;
    $('#tabContent').innerHTML = empty('Sem avaliações ainda', 'Crie sua primeira avaliação para começar.', 'new-project', 'Nova avaliação'); return;
  }
  $('#editProjectBtn').hidden = false; $('#deleteProjectBtn').hidden = false; $('#addFindingTop').disabled = false;
  renderSidebar(p);
  $('#crumbTitle').textContent = p.name;
  $('#projectTitle').textContent = p.name;
  $('#projectTypeBadge').textContent = TYPES[p.type].label.toUpperCase();
  $('#projectDate').textContent = `Criado em ${date(p.createdAt)}`;
  $('#projectDescription').textContent = p.description || 'Adicione uma descrição para registrar o objetivo e o escopo desta avaliação.';
  $('#heroTags').innerHTML = p.categories.map(c => `<span class="tag">${CATEGORIES[c].label}</span>`).join('');
  const pr = progress(p), open = openFindings(p), top = priority(p);
  $('#metricProgress').textContent = `${pr.pct}%`;
  $('#metricProgressDetail').textContent = `${pr.done} de ${pr.total} verificados`;
  $('#progressFill').style.width = `${pr.pct}%`;
  $('#metricOpen').textContent = open.length;
  $('#metricOpenDetail').textContent = open.length ? `${open.filter(f => f.status === 'open').length} aguardando triagem` : 'Nenhuma pendência';
  $('#metricPriority').textContent = top ? SEVERITIES[top].label : '—';
  $('#metricPriorityDetail').textContent = top ? 'Maior severidade em aberto' : 'Sem achados em aberto';
  $('#tabChecklistCount').textContent = activeItems(p).length;
  $('#tabFindingsCount').textContent = p.findings.length;
  document.querySelectorAll('.tab').forEach(b => { const active = b.dataset.tab === tab; b.classList.toggle('active', active); b.setAttribute('aria-selected', active); });
  $('#tabContent').innerHTML = tab === 'overview' ? overview(p) : tab === 'checklist' ? checklist(p) : findings(p);
}

function overview(p) {
  const groups = p.categories.map(c => {
    const subset = activeItems(p).filter(i => i.category === c), done = subset.filter(i => i.status !== 'pending').length, pct = subset.length ? Math.round(done / subset.length * 100) : 0;
    return `<div class="category-row"><span class="cat-icon">${CATEGORIES[c].icon}</span><div><div class="cat-title">${CATEGORIES[c].label}</div><div class="cat-detail">${done} de ${subset.length} verificados</div></div><span class="cat-bar"><i style="width:${pct}%"></i></span><span class="cat-pct">${pct}%</span></div>`;
  }).join('');
  const link = validLink(p.reference);
  return `<div class="overview-grid"><div class="panel"><div class="panel-head"><h3>Cobertura da avaliação</h3><span class="panel-sub">${p.categories.length} categorias ativas</span></div><div class="category-list">${groups}</div></div><div class="panel"><div class="panel-head"><h3>Contexto do projeto</h3><span class="panel-sub">${TYPES[p.type].label}</span></div><dl class="context-list"><div><dt>STACK / FERRAMENTAS</dt><dd>${esc(p.stack) || 'Ainda não informado'}</dd></div><div><dt>REFERÊNCIA</dt><dd>${link ? `<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(p.reference)} ↗</a>` : esc(p.reference) || 'Ainda não informado'}</dd></div><div><dt>ÚLTIMA ATUALIZAÇÃO</dt><dd>${date(p.updatedAt)}</dd></div></dl></div></div><div class="hint"><strong>Próximo passo:</strong> abra o checklist, marque cada validação e registre um achado quando encontrar um problema. Esta versão organiza a revisão manual; não executa testes ou varreduras de código automaticamente.</div>`;
}

function checklist(p) {
  const items = activeItems(p);
  const filtered = checklistFilter === 'all' ? items : items.filter(i => i.status === checklistFilter);
  const groups = p.categories.map(c => {
    const rows = filtered.filter(i => i.category === c);
    if (!rows.length) return '';
    return `<div class="checklist-group"><div class="checklist-group-head"><span class="cat-icon" style="width:23px;height:23px;font-size:12px">${CATEGORIES[c].icon}</span>${CATEGORIES[c].label}<small>${rows.length} verificações</small></div>${rows.map(i => `<div class="check-row"><div><div class="check-title">${esc(i.title)}</div>${i.custom ? '<div class="check-meta">Adicionado por você</div>' : ''}</div><select class="status-select" aria-label="Status: ${esc(i.title)}" data-item-status="${esc(i.id)}">${Object.entries(STATUSES).map(([v, name]) => `<option value="${v}" ${i.status === v ? 'selected' : ''}>${name}</option>`).join('')}</select><button class="mini-btn" data-find-from="${esc(i.id)}">＋ Achado</button></div>`).join('')}</div>`;
  }).join('');
  return `<div class="list-heading"><div><h3>Verificações</h3><p>Registre o resultado de cada teste e vincule os problemas encontrados.</p></div><div class="toolbar"><select class="filter-select" id="checkFilter" aria-label="Filtrar verificações"><option value="all">Todos os status</option>${Object.entries(STATUSES).map(([v,n]) => `<option value="${v}" ${checklistFilter === v ? 'selected' : ''}>${n}</option>`).join('')}</select><button class="button button-outline" data-action="add-item">＋ Verificação</button></div></div>${groups || empty('Nenhuma verificação neste filtro', 'Mude o filtro ou adicione um teste ao checklist.', 'add-item', 'Adicionar verificação')}`;
}

function findings(p) {
  const needle = findingSearch.trim().toLocaleLowerCase('pt-BR');
  const list = [...p.findings].filter(f => (findingFilter === 'all' || f.status === findingFilter) && (!needle || `${f.title} ${f.description} ${f.category}`.toLocaleLowerCase('pt-BR').includes(needle))).sort((a,b) => SEVERITIES[b.severity].rank - SEVERITIES[a.severity].rank);
  const cards = list.map(f => `<article class="finding-card"><span class="severity-line ${f.severity}"></span><div><div class="finding-title">${esc(f.title)}</div><div class="finding-meta"><span class="pill ${f.severity}">${SEVERITIES[f.severity].label}</span><span class="pill">${CATEGORIES[f.category].label}</span><span class="pill">${FINDING_STATUSES[f.status]}</span></div><p class="finding-desc">${esc(f.description)}</p>${f.steps ? `<p class="finding-desc"><strong>Reprodução:</strong> ${esc(f.steps)}</p>` : ''}${f.evidence ? `<p class="finding-desc"><strong>Evidência:</strong> ${esc(f.evidence)}</p>` : ''}</div><div class="finding-actions"><button data-edit-finding="${esc(f.id)}" aria-label="Editar ${esc(f.title)}">✎ Editar</button><button data-delete-finding="${esc(f.id)}" aria-label="Excluir ${esc(f.title)}">×</button></div></article>`).join('');
  return `<div class="list-heading"><div><h3>Achados registrados</h3><p>Priorize por severidade e acompanhe a correção.</p></div><div class="toolbar"><input class="search-input" id="findingSearch" aria-label="Buscar achados" placeholder="Buscar achados..." value="${esc(findingSearch)}" /><select class="filter-select" id="findingFilter" aria-label="Filtrar achados"><option value="all">Todos os status</option>${Object.entries(FINDING_STATUSES).map(([v,n]) => `<option value="${v}" ${findingFilter === v ? 'selected' : ''}>${n}</option>`).join('')}</select></div></div><div class="finding-list">${cards || empty('Nenhum achado encontrado', p.findings.length ? 'Ajuste a busca ou o filtro.' : 'Registre o primeiro problema encontrado durante a revisão.', 'add-finding', 'Registrar achado')}</div>`;
}

function projectDialog(project = null) {
  editProjectId = project?.id ?? null;
  const form = $('#projectForm'); form.reset();
  $('#projectDialogTitle').textContent = project ? 'Editar avaliação' : 'Nova avaliação';
  form.elements.name.value = project?.name ?? '';
  form.elements.type.value = project?.type ?? 'api';
  form.elements.description.value = project?.description ?? '';
  form.elements.stack.value = project?.stack ?? '';
  form.elements.reference.value = project?.reference ?? '';
  $('#categoryOptions').innerHTML = Object.entries(CATEGORIES).map(([key,c]) => `<label class="category-option"><input type="checkbox" name="categories" value="${key}" ${!project || project.categories.includes(key) ? 'checked' : ''} />${c.icon} ${c.label}</label>`).join('');
  show($('#projectDialog'));
}

function findingDialog(finding = null, itemId = '') {
  const p = current(); editFindingId = finding?.id ?? null;
  const form = $('#findingForm'); form.reset();
  $('#findingDialogTitle').textContent = finding ? 'Editar achado' : 'Registrar achado';
  $('#findingCategory').innerHTML = categorySelectOptions(p);
  $('#findingItem').innerHTML = '<option value="">Sem vínculo</option>' + p.items.map(i => `<option value="${esc(i.id)}">${esc(i.title)}</option>`).join('');
  form.elements.title.value = finding?.title ?? '';
  form.elements.category.value = finding?.category ?? p.items.find(i => i.id === itemId)?.category ?? p.categories[0];
  form.elements.severity.value = finding?.severity ?? 'medium';
  form.elements.status.value = finding?.status ?? 'open';
  form.elements.itemId.value = finding?.itemId ?? itemId;
  form.elements.description.value = finding?.description ?? '';
  form.elements.steps.value = finding?.steps ?? '';
  form.elements.evidence.value = finding?.evidence ?? '';
  show($('#findingDialog'));
}

$('#projectForm').addEventListener('submit', e => {
  e.preventDefault(); const form = e.currentTarget; const data = new FormData(form);
  const name = String(data.get('name') ?? '').trim(), categories = data.getAll('categories'), type = data.get('type');
  if (!name) { form.elements.name.focus(); notify('Dê um nome ao projeto.'); return; }
  if (!categories.length) { notify('Selecione ao menos uma categoria de teste.'); return; }
  if (editProjectId) {
    const p = projects.find(x => x.id === editProjectId);
    Object.assign(p, { name, type, categories, description: String(data.get('description') ?? '').trim(), stack: String(data.get('stack') ?? '').trim(), reference: String(data.get('reference') ?? '').trim() });
    syncTemplates(p); touch(p);
  } else {
    const p = createProject({ name, type, categories, description: String(data.get('description') ?? ''), stack: String(data.get('stack') ?? ''), reference: String(data.get('reference') ?? '') });
    projects.unshift(p); currentId = p.id; tab = 'overview'; save(); render();
  }
  $('#projectDialog').close(); notify(editProjectId ? 'Avaliação atualizada.' : 'Avaliação criada.');
});

$('#findingForm').addEventListener('submit', e => {
  e.preventDefault(); const form = e.currentTarget; const data = new FormData(form), p = current();
  const title = String(data.get('title') ?? '').trim(), description = String(data.get('description') ?? '').trim();
  if (!title || !description) { notify('Informe título e descrição do achado.'); (!title ? form.elements.title : form.elements.description).focus(); return; }
  const fields = { title, description, category: data.get('category'), severity: data.get('severity'), status: data.get('status'), itemId: data.get('itemId'), steps: String(data.get('steps') ?? '').trim(), evidence: String(data.get('evidence') ?? '').trim() };
  if (editFindingId) Object.assign(p.findings.find(f => f.id === editFindingId), fields);
  else p.findings.unshift({ id: uid(), ...fields, createdAt: new Date().toISOString() });
  $('#findingDialog').close(); tab = 'findings'; touch(p); notify(editFindingId ? 'Achado atualizado.' : 'Achado registrado.');
});

$('#itemForm').addEventListener('submit', e => {
  e.preventDefault(); const data = new FormData(e.currentTarget), p = current(), title = String(data.get('title') ?? '').trim();
  if (!title) return;
  p.items.push({ id: uid(), title, category: data.get('category'), status: 'pending', custom: true });
  $('#itemDialog').close(); e.currentTarget.reset(); tab = 'checklist'; touch(p); notify('Verificação adicionada.');
});

document.addEventListener('click', e => {
  const target = e.target.closest('button'); if (!target) return;
  if (target.hasAttribute('data-close')) { target.closest('dialog').close(); return; }
  if (target.dataset.project) { currentId = target.dataset.project; tab = 'overview'; render(); return; }
  if (target.dataset.tab) { tab = target.dataset.tab; render(); return; }
  if (target.dataset.findFrom) { findingDialog(null, target.dataset.findFrom); return; }
  if (target.dataset.editFinding) { findingDialog(current().findings.find(f => f.id === target.dataset.editFinding)); return; }
  if (target.dataset.deleteFinding) {
    if (target.dataset.confirm !== 'yes') { target.dataset.confirm = 'yes'; target.textContent = 'Confirmar'; setTimeout(() => { if (target.isConnected) { target.dataset.confirm = ''; target.textContent = '×'; } }, 4000); return; }
    const p = current(); p.findings = p.findings.filter(f => f.id !== target.dataset.deleteFinding); touch(p); notify('Achado excluído.'); return;
  }
  if (target.dataset.action === 'new-project') projectDialog();
  if (target.dataset.action === 'add-finding') findingDialog();
  if (target.dataset.action === 'add-item') openItemDialog();
});

function openItemDialog() { $('#itemCategory').innerHTML = categorySelectOptions(current()); show($('#itemDialog')); }
document.addEventListener('change', e => {
  if (e.target.dataset.itemStatus) { const p = current(), item = p.items.find(i => i.id === e.target.dataset.itemStatus); if (item) { item.status = e.target.value; touch(p); } }
  if (e.target.id === 'checkFilter') { checklistFilter = e.target.value; render(); }
  if (e.target.id === 'findingFilter') { findingFilter = e.target.value; render(); }
  if (e.target.id === 'mobileProjects') { currentId = e.target.value; tab = 'overview'; render(); }
});
document.addEventListener('input', e => {
  if (e.target.id === 'findingSearch') { findingSearch = e.target.value; const start = e.target.selectionStart; render(); $('#findingSearch').focus(); $('#findingSearch').setSelectionRange(start, start); }
});

$('#newProjectBtn').addEventListener('click', () => projectDialog());
$('#addProjectSide').addEventListener('click', () => projectDialog());
$('#editProjectBtn').addEventListener('click', () => projectDialog(current()));
$('#addFindingTop').addEventListener('click', () => findingDialog());
$('#deleteProjectBtn').addEventListener('click', e => {
  const btn = e.currentTarget;
  if (btn.dataset.confirm !== 'yes') { btn.dataset.confirm = 'yes'; btn.textContent = 'Confirmar exclusão'; setTimeout(() => { btn.dataset.confirm = ''; btn.textContent = 'Excluir'; }, 5000); return; }
  projects = projects.filter(p => p.id !== currentId); currentId = projects[0]?.id ?? null;
  btn.dataset.confirm = ''; btn.textContent = 'Excluir'; tab = 'overview'; save(); render(); notify('Avaliação excluída.');
});
$('#exportBtn').addEventListener('click', () => {
  const json = JSON.stringify({ format: 'prismaqa-v1', exportedAt: new Date().toISOString(), projects }, null, 2);
  const href = URL.createObjectURL(new Blob([json], { type: 'application/json' }));
  const anchor = document.createElement('a'); anchor.href = href; anchor.download = `prismaqa-backup-${new Date().toISOString().slice(0,10)}.json`; anchor.click(); setTimeout(() => URL.revokeObjectURL(href), 1000); notify('Backup exportado.');
});
$('#importBtn').addEventListener('click', () => $('#importFile').click());
$('#importFile').addEventListener('change', async e => {
  const file = e.target.files?.[0]; if (!file) return;
  try {
    if (file.size > 5_000_000) throw new Error('O arquivo excede 5 MB.');
    const imported = validateBackup(JSON.parse(await file.text()));
    const byId = new Map(projects.map(p => [p.id, p]));
    for (const p of imported) byId.set(p.id, p);
    projects = [...byId.values()]; currentId = imported[0]?.id ?? currentId; save(); render(); notify(`${imported.length} avaliação(ões) importada(s).`);
  } catch (error) { notify(error.message || 'Não foi possível importar o arquivo.'); }
  e.target.value = '';
});

save(); render();
