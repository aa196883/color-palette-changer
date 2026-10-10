const $ = id => document.getElementById(id);
let currentPalette = null, currentMapping = null, lastMapping = null;
let images = [], palettes = [];

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed.');
  return {data, response};
}
const post = data => ({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
async function run(work) {
  const controls = [...document.querySelectorAll('button, input, select')];
  const disabled = controls.map(control => control.disabled);
  controls.forEach(control => control.disabled = true);
  status('Working…');
  try { await work(); } catch (error) { status(error.message, true); }
  finally {
    controls.forEach((control, i) => control.disabled = disabled[i]);
    $('palette-save').disabled = !currentPalette || currentPalette.saved;
    $('palette-reroll').disabled = !currentPalette;
    $('map-save').disabled = !currentMapping || currentMapping.saved;
    $('map-reroll').disabled = !lastMapping;
  }
}
function options(select, items, selected, label) {
  select.replaceChildren(new Option(label, ''));
  items.forEach(item => select.add(new Option(item.name || `${item.palette_size} colors · ${item.id}`, item.id)));
  select.value = selected || '';
}
async function refresh() {
  const [p, i] = await Promise.all([api('/api/palettes'), api('/api/images')]);
  const drafts = palettes.filter(palette => !palette.saved && !p.data.palettes.some(saved => saved.id === palette.id));
  palettes = [...p.data.palettes, ...drafts]; images = i.data.images;
  if (currentPalette && !palettes.some(p => p.id === currentPalette.id)) palettes.unshift(currentPalette);
  options($('palette-select'), palettes, currentPalette?.id || $('palette-select').value, 'Choose a palette');
  options($('image-select'), images, $('image-select').value, 'Choose an image');
}
function showPalette(data, id, saved = false) {
  currentPalette = {...data, id, saved};
  $('swatches').replaceChildren();
  data.colors.forEach(color => {
    const swatch = document.createElement('div'); swatch.className = 'swatch'; swatch.style.backgroundColor = color;
    const text = document.createElement('span'); text.textContent = color; swatch.append(text); $('swatches').append(swatch);
  });
  $('palette-detail').textContent = `${data.palette_size} colors · Seed ${data.seed || 'not recorded'}`;
  $('palette-download').href = `/api/palettes/${encodeURIComponent(id)}?download=1`;
  $('palette-download').hidden = false;
}
async function generate(reroll) {
  const {data, response} = await api('/api/palettes', post({
    seed: reroll ? null : $('seed').value.trim() || null,
    palette_size: Number($('size').value), lightness_step: Number($('lightness').value),
    green_red_step: Number($('red').value), blue_yellow_step: Number($('yellow').value)
  }));
  showPalette(data, response.headers.get('X-Palette-ID'));
  await refresh(); status('Palette ready. Save it to your library or reroll the seed.');
}
$('generate-form').addEventListener('submit', event => {event.preventDefault(); run(() => generate(false));});
$('palette-reroll').onclick = () => run(() => generate(true));
$('palette-save').onclick = () => run(async () => {
  await api(`/api/palettes/${encodeURIComponent(currentPalette.id)}/save`, {method: 'POST'});
  currentPalette.saved = true; await refresh(); status('Palette saved to palettes/. Download JSON to keep another copy.');
});
$('palette-select').onchange = () => run(async () => {
  const id = $('palette-select').value;
  if (!id) {status('Choose a palette to map.'); return;}
  const {data} = await api(`/api/palettes/${encodeURIComponent(id)}`);
  showPalette(data, id, palettes.find(p => p.id === id).saved); status('Palette selected.');
});
function showOriginal() {
  const image = images.find(image => image.id === $('image-select').value);
  $('original').hidden = !image; $('original-empty').hidden = !!image;
  if (image) $('original').src = image.url;
}
$('image-select').onchange = showOriginal;
$('upload').onchange = () => run(async () => {
  const file = $('upload').files[0]; if (!file) return;
  const form = new FormData(); form.append('image', file);
  const {data} = await api('/api/images', {method: 'POST', body: form});
  await refresh(); $('image-select').value = data.id; showOriginal(); $('upload').value = ''; status('Image uploaded and ready to map.');
});
async function map(reroll) {
  const parameters = reroll ? lastMapping : {palette_id: $('palette-select').value, image_id: $('image-select').value, image_mapping: $('mode').value};
  if (!parameters.palette_id || !parameters.image_id) throw new Error('Choose a palette and an image first.');
  const {data} = await api('/api/mappings', post(parameters));
  lastMapping = {...parameters}; currentMapping = data;
  $('image-select').value = parameters.image_id; showOriginal();
  $('palette-select').value = parameters.palette_id; $('mode').value = parameters.image_mapping;
  const palette = await api(`/api/palettes/${encodeURIComponent(parameters.palette_id)}`);
  showPalette(palette.data, parameters.palette_id, !!palettes.find(p => p.id === parameters.palette_id)?.saved);
  $('result').src = data.url; $('result').hidden = false; $('result-empty').hidden = true;
  $('image-download').href = data.url + '?download=1'; $('image-download').hidden = false;
  status('Mapping ready. Save this image or reroll its color assignment.');
}
$('map').onclick = () => run(() => map(false));
$('map-reroll').onclick = () => run(() => map(true));
$('map-save').onclick = () => run(async () => {
  const {data} = await api(`/api/images/${encodeURIComponent(currentMapping.id)}/save`, {method: 'POST'});
  currentMapping = data; $('image-download').href = data.url + '?download=1';
  await refresh(); status('Image saved to outputs/. Download PNG to keep another copy.');
});
run(async () => {await refresh(); status('Generate a palette or choose one from your library.');});
