const $ = id => document.getElementById(id);
let generatedPalette = null;
let augmentedPalette = null;
let currentMapping = null;
let lastMapping = null;
let lastAugmentation = null;
let images = [];
let palettes = [];

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
    controls.forEach((control, index) => control.disabled = disabled[index]);
    $('palette-save').disabled = !generatedPalette || generatedPalette.saved;
    $('palette-reroll').disabled = !generatedPalette;
    $('augmentation-save').disabled = !augmentedPalette || augmentedPalette.saved;
    $('augmentation-reroll').disabled = !lastAugmentation;
    $('map-save').disabled = !currentMapping || currentMapping.saved;
    $('map-reroll').disabled = !lastMapping;
  }
}

function options(select, items, selected, label) {
  select.replaceChildren(new Option(label, ''));
  items.forEach(item => select.add(new Option(item.name || `${item.palette_size} colors · ${item.id}`, item.id)));
  select.value = selected || '';
}

function renderPaletteSnapshots(selectedId, selectId = 'palette-select', containerId = 'palette-snapshots') {
  const container = $(containerId);
  container.replaceChildren();
  if (!palettes.length) {
    const empty = document.createElement('p'); empty.className = 'hint'; empty.textContent = 'No saved palettes.';
    container.append(empty); return;
  }
  palettes.forEach(palette => {
    const option = document.createElement('button');
    option.type = 'button'; option.className = 'palette-snapshot';
    option.dataset.paletteId = palette.id; option.setAttribute('role', 'option');
    option.setAttribute('aria-selected', String(palette.id === selectedId));
    if (palette.id === selectedId) option.classList.add('selected');
    const strip = document.createElement('span'); strip.className = 'palette-snapshot-colors';
    palette.colors.forEach(color => {
      const swatch = document.createElement('span'); swatch.style.backgroundColor = color; swatch.title = color;
      strip.append(swatch);
    });
    const name = document.createElement('strong'); name.textContent = palette.name || palette.id;
    const size = document.createElement('small'); size.textContent = `${palette.palette_size} colors`;
    option.append(strip, name, size);
    option.onclick = () => {
      $(selectId).value = palette.id;
      $(selectId).dispatchEvent(new Event('change'));
    };
    container.append(option);
  });
}

async function refresh() {
  const [paletteResponse, imageResponse] = await Promise.all([api('/api/palettes'), api('/api/images')]);
  const savedPalettes = paletteResponse.data.palettes;
  const drafts = palettes.filter(palette => !palette.saved && !savedPalettes.some(saved => saved.id === palette.id));
  palettes = [...savedPalettes, ...drafts];
  [generatedPalette, augmentedPalette].filter(Boolean).forEach(preview => {
    if (!palettes.some(palette => palette.id === preview.id)) palettes.unshift(preview);
  });
  images = imageResponse.data.images.filter(image => image.id.startsWith('inputs:'));
  const selectedPalette = $('palette-select').value;
  options($('palette-select'), palettes, selectedPalette, 'Choose a palette');
  renderPaletteSnapshots(selectedPalette, 'palette-select', 'palette-snapshots');
  options($('augmentation-source'), palettes, $('augmentation-source').value, 'Choose a palette');
  renderPaletteSnapshots($('augmentation-source').value, 'augmentation-source', 'augmentation-palette-snapshots');
  options($('image-select'), images, $('image-select').value, 'Choose an image');
}

function renderPalettePreview(data, id, kind) {
  const prefix = kind === 'augmentation' ? 'augmentation-' : 'palette-';
  const swatches = $(kind === 'augmentation' ? 'augmentation-swatches' : 'swatches');
  swatches.replaceChildren();
  data.colors.forEach(color => {
    const swatch = document.createElement('div'); swatch.className = 'swatch'; swatch.style.backgroundColor = color;
    const text = document.createElement('span'); text.textContent = color; swatch.append(text); swatches.append(swatch);
  });
  $(`${prefix}detail`).textContent = `${data.palette_size} colors · Seed ${data.seed || 'not recorded'}`;
  $(`${prefix}download`).href = `/api/palettes/${encodeURIComponent(id)}?download=1`;
  $(`${prefix}download`).hidden = false;
}

function showPalette(data, id, saved = false, kind = 'generated') {
  const preview = {...data, id, saved, kind};
  palettes = [...palettes.filter(palette => palette.id !== id), preview];
  options($('palette-select'), palettes, id, 'Choose a palette');
  options($('augmentation-source'), palettes,
    kind === 'generated' ? id : $('augmentation-source').value, 'Choose a palette');
  if (kind === 'augmentation') augmentedPalette = preview;
  else {
    generatedPalette = preview;
    $('augmentation-source').value = id;
  }
  $('palette-select').value = id;
  $('augmentation-source').value = kind === 'generated' ? id : $('augmentation-source').value;
  renderPaletteSnapshots(id, 'palette-select', 'palette-snapshots');
  renderPaletteSnapshots($('augmentation-source').value, 'augmentation-source', 'augmentation-palette-snapshots');
  renderPalettePreview(data, id, kind);
}

async function generate(reroll) {
  const mode = $('generation-mode').value;
  const {data, response} = await api('/api/palettes', post({
    mode,
    seed: reroll ? null : $('seed').value.trim() || null,
    palette_size: Number($('size').value),
    ...(mode === 'analogous' ? {
      lightness_step: Number($('lightness').value),
      green_red_step: Number($('red').value), blue_yellow_step: Number($('yellow').value)
    } : {})
  }));
  showPalette(data, response.headers.get('X-Palette-ID'), false, 'generated');
  await refresh(); status('Palette ready. Save it to your library or reroll the seed.');
}

function optionalNumber(id) {
  const value = $(id).value.trim();
  return value === '' ? undefined : Number(value);
}

async function augment() {
  const sourceId = $('augmentation-source').value;
  if (!sourceId) throw new Error('Choose a source palette first.');
  const lightness = optionalNumber('augmentation-lightness');
  const greenRed = optionalNumber('augmentation-red');
  const blueYellow = optionalNumber('augmentation-yellow');
  const parameters = {
    factor: Number($('augmentation-factor').value),
    ...(lightness === undefined ? {} : {lightness_step: lightness}),
    ...(greenRed === undefined ? {} : {green_red_step: greenRed}),
    ...(blueYellow === undefined ? {} : {blue_yellow_step: blueYellow})
  };
  const {data, response} = await api(`/api/palettes/${encodeURIComponent(sourceId)}/augment`, post(parameters));
  lastAugmentation = {sourceId, parameters};
  showPalette(data, response.headers.get('X-Palette-ID'), false, 'augmentation');
  await refresh(); status('Augmented palette ready. Adjust the steps or save it.');
}

function updateGenerationMode() {
  const complementary = $('generation-mode').value === 'complementary';
  ['lightness', 'red', 'yellow'].forEach(id => { $(id).disabled = complementary; });
  $('generation-help').textContent = complementary
    ? 'Complementary uses seed lightness and a new random line on each generation. Step values are ignored.'
    : 'Analogous uses the seed color and step values.';
}

async function savePalette(preview, nameField) {
  const oldId = preview.id;
  const name = $(nameField).value.trim();
  const options = name ? post({name}) : {method: 'POST'};
  const {data} = await api(`/api/palettes/${encodeURIComponent(oldId)}/save`, options);
  palettes = palettes.filter(palette => palette.id !== oldId);
  const saved = {...preview, ...data, id: data.id, saved: true};
  if (preview.kind === 'augmentation') augmentedPalette = saved;
  else {
    generatedPalette = saved;
    if ($('augmentation-source').value === oldId) $('augmentation-source').value = data.id;
  }
  $('palette-select').value = data.id;
  renderPaletteSnapshots(data.id, 'palette-select', 'palette-snapshots');
  renderPaletteSnapshots($('augmentation-source').value, 'augmentation-source', 'augmentation-palette-snapshots');
  renderPalettePreview(saved, data.id, preview.kind);
  await refresh(); status('Palette saved to palettes/. Download JSON to keep another copy.');
}

function showOriginal() {
  const image = images.find(item => item.id === $('image-select').value);
  $('original').hidden = !image; $('original-empty').hidden = !!image;
  if (image) $('original').src = image.url;
}

async function map(reroll) {
  const parameters = reroll ? lastMapping : {palette_id: $('palette-select').value, image_id: $('image-select').value, image_mapping: $('mode').value};
  if (!parameters.palette_id || !parameters.image_id) throw new Error('Choose a palette and an image first.');
  const {data} = await api('/api/mappings', post(parameters));
  lastMapping = {...parameters}; currentMapping = data;
  $('image-select').value = parameters.image_id; showOriginal();
  $('palette-select').value = parameters.palette_id; $('mode').value = parameters.image_mapping;
  $('result').src = data.url; $('result').hidden = false; $('result-empty').hidden = true;
  $('image-download').href = data.url + '?download=1'; $('image-download').hidden = false;
  status('Mapping ready. Save this image or reroll its color assignment.');
}

$('generation-mode').addEventListener('change', updateGenerationMode);
updateGenerationMode();
$('generate-form').addEventListener('submit', event => { event.preventDefault(); run(() => generate(false)); });
$('palette-reroll').onclick = () => run(() => generate(true));
$('palette-save').onclick = () => run(() => savePalette(generatedPalette, 'palette-name'));
$('augmentation-form').addEventListener('submit', event => { event.preventDefault(); run(() => augment()); });
$('augmentation-reroll').onclick = () => run(async () => {
  if (!lastAugmentation) return;
  $('augmentation-source').value = lastAugmentation.sourceId;
  $('augmentation-factor').value = lastAugmentation.parameters.factor;
  const {data, response} = await api(`/api/palettes/${encodeURIComponent(lastAugmentation.sourceId)}/augment`, post(lastAugmentation.parameters));
  showPalette(data, response.headers.get('X-Palette-ID'), false, 'augmentation');
  await refresh(); status('Augmented palette rerolled.');
});
$('augmentation-save').onclick = () => run(() => savePalette(augmentedPalette, 'augmentation-name'));
$('palette-select').onchange = () => run(async () => {
  const id = $('palette-select').value;
  if (!id) { status('Choose a palette to map.'); return; }
  await api(`/api/palettes/${encodeURIComponent(id)}`);
  $('augmentation-source').value = id;
  renderPaletteSnapshots(id, 'palette-select', 'palette-snapshots');
  renderPaletteSnapshots(id, 'augmentation-source', 'augmentation-palette-snapshots'); status('Palette selected.');
});
$('augmentation-source').onchange = () => {
  renderPaletteSnapshots($('augmentation-source').value, 'augmentation-source', 'augmentation-palette-snapshots');
};
$('image-select').onchange = showOriginal;
$('upload').onchange = () => run(async () => {
  const file = $('upload').files[0]; if (!file) return;
  const form = new FormData(); form.append('image', file);
  const {data} = await api('/api/images', {method: 'POST', body: form});
  await refresh(); $('image-select').value = data.id; showOriginal(); $('upload').value = ''; status('Image uploaded and ready to map.');
});
$('map').onclick = () => run(() => map(false));
$('map-reroll').onclick = () => run(() => map(true));
$('map-save').onclick = () => run(async () => {
  const {data} = await api(`/api/images/${encodeURIComponent(currentMapping.id)}/save`, {method: 'POST'});
  currentMapping = data; $('image-download').href = data.url + '?download=1';
  await refresh(); status('Image saved to outputs/. Download PNG to keep another copy.');
});
run(async () => { await refresh(); status('Generate a palette or choose one from your library.'); });
