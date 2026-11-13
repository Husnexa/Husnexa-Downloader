// Husnexa - Liquid Glass Engine & Animation Controller
// Husnexa UI

let currentMode = 'single'; // 'single' | 'bulk'
let selectedMediaType = 'video'; // 'video' | 'audio'
let selectedVideoQuality = 'best';
let selectedAudioQuality = 'MP3';
let currentSingleData = null;
let currentBulkData = null;
let isDownloading = false;
let isPaused = false;
let activeQueueJob = null;
let autoCookiesEnabled = true;
let selectedCookieBrowser = 'none';

// Remote text (titles, errors) must pass through this before entering any HTML template.
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

// DOM Elements
const docEl = document.documentElement;
const themeToggleBtn = document.getElementById('themeToggleBtn');
const themeIcon = document.getElementById('themeIcon');
const themeLabel = document.getElementById('themeLabel');

const tabSingleBtn = document.getElementById('tabSingleBtn');
const tabBulkBtn = document.getElementById('tabBulkBtn');
const tabGlider = document.getElementById('tabGlider');
const singleSection = document.getElementById('singleSection');
const bulkSection = document.getElementById('bulkSection');

const singleUrlInput = document.getElementById('singleUrlInput');
const pasteBtn = document.getElementById('pasteBtn');
const analyzeBtn = document.getElementById('analyzeBtn');

const previewCard = document.getElementById('previewCard');
const previewThumb = document.getElementById('previewThumb');
const previewPlatform = document.getElementById('previewPlatform');
const previewDuration = document.getElementById('previewDuration');
const previewTitle = document.getElementById('previewTitle');
const previewChannel = document.getElementById('previewChannel');

const formatNav = document.getElementById('formatNav');
const formatGlider = document.getElementById('formatGlider');
const typeVideoBtn = document.getElementById('typeVideoBtn');
const typeAudioBtn = document.getElementById('typeAudioBtn');
const videoResolutionsSection = document.getElementById('videoResolutionsSection');
const resolutionsGrid = document.getElementById('resolutionsGrid');
const audioQualitySection = document.getElementById('audioQualitySection');
const audioMp3Btn = document.getElementById('audioMp3Btn');
const audioM4aBtn = document.getElementById('audioM4aBtn');
const audioWavBtn = document.getElementById('audioWavBtn');
const audioMp3Size = document.getElementById('audioMp3Size');
const audioM4aSize = document.getElementById('audioM4aSize');
const audioWavSize = document.getElementById('audioWavSize');

// Single Clip Trimmer & Toggles
const clipStartInput = document.getElementById('clipStartInput');
const clipEndInput = document.getElementById('clipEndInput');
const embedSubsCheck = document.getElementById('embedSubsCheck');
const embedMetaCheck = document.getElementById('embedMetaCheck');

const destPathText = document.getElementById('destPathText');
const browseDestBtn = document.getElementById('browseDestBtn');
const openDestBtn = document.getElementById('openDestBtn');

const turboCheck = document.getElementById('turboCheck');
const cookiesBtn = document.getElementById('cookiesBtn');
const cookiesLabel = document.getElementById('cookiesLabel');

// Anti-Bot / Cookies Modal Elements
const cookiesModalOverlay = document.getElementById('cookiesModalOverlay');
const closeCookiesModalBtn = document.getElementById('closeCookiesModalBtn');
const dismissCookiesBtn = document.getElementById('dismissCookiesBtn');
const currentCookieBadge = document.getElementById('currentCookieBadge');
const autoCookiesCheck = document.getElementById('autoCookiesCheck');
const importCookiesFileBtn = document.getElementById('importCookiesFileBtn');
const cookieBrowserBtns = document.querySelectorAll('.cookie-browser-btn');

// Bulk Elements
const bulkTextarea = document.getElementById('bulkTextarea');
const bulkPasteBtn = document.getElementById('bulkPasteBtn');
const analyzeBulkBtn = document.getElementById('analyzeBulkBtn');
const bulkOptionsCard = document.getElementById('bulkOptionsCard');
const bulkSummaryText = document.getElementById('bulkSummaryText');
const bulkSelectAllBtn = document.getElementById('bulkSelectAllBtn');
const bulkResCapSelect = document.getElementById('bulkResCapSelect');
const bulkResCapWrapper = document.getElementById('bulkResCapWrapper');
const bulkItemsList = document.getElementById('bulkItemsList');
const bulkTypeVideo = document.getElementById('bulkTypeVideo');
const bulkTypeMp3 = document.getElementById('bulkTypeMp3');
const bulkTypeWav = document.getElementById('bulkTypeWav');

const progressCard = document.getElementById('progressCard');
const progressTitle = document.getElementById('progressTitle');
const progressPercent = document.getElementById('progressPercent');
const progressFill = document.getElementById('progressFill');
const progressSpeed = document.getElementById('progressSpeed');
const progressEta = document.getElementById('progressEta');
const progressSize = document.getElementById('progressSize');

const startDownloadBtn = document.getElementById('startDownloadBtn');
const downloadBtnIcon = document.getElementById('downloadBtnIcon');
const downloadBtnText = document.getElementById('downloadBtnText');

const downloadControlsRow = document.getElementById('downloadControlsRow');
const pauseDownloadBtn = document.getElementById('pauseDownloadBtn');
const pauseBtnIcon = document.getElementById('pauseBtnIcon');
const pauseBtnText = document.getElementById('pauseBtnText');
const cancelDownloadBtn = document.getElementById('cancelDownloadBtn');
const miniPauseBtn = document.getElementById('miniPauseBtn');
const miniCancelBtn = document.getElementById('miniCancelBtn');

// Post-Download Action Bar Elements
const postDownloadBar = document.getElementById('postDownloadBar');
const openFileBtn = document.getElementById('openFileBtn');
const openFileIcon = document.getElementById('openFileIcon');
const openFileLabel = document.getElementById('openFileLabel');
const showFolderBtn = document.getElementById('showFolderBtn');
const newDownloadBtn = document.getElementById('newDownloadBtn');

// Smart Clipboard Auto-Detect Elements
const clipboardPill = document.getElementById('clipboardPill');
const clipboardUrlText = document.getElementById('clipboardUrlText');
const clipboardAnalyzeBtn = document.getElementById('clipboardAnalyzeBtn');
const clipboardDismissBtn = document.getElementById('clipboardDismissBtn');

// History Drawer Elements
const historyBtn = document.getElementById('historyBtn');
const historyBadge = document.getElementById('historyBadge');
const historyModalOverlay = document.getElementById('historyModalOverlay');
const closeHistoryModalBtn = document.getElementById('closeHistoryModalBtn');
const dismissHistoryBtn = document.getElementById('dismissHistoryBtn');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const historyList = document.getElementById('historyList');
const historyCountSubtitle = document.getElementById('historyCountSubtitle');

let lastDownloadedFilePath = null;
let lastDismissedClipboardUrl = null;

// Update & System DOM Elements
const updateBtn = document.getElementById('updateBtn');
const updateBtnIcon = document.getElementById('updateBtnIcon');
const updateBtnLabel = document.getElementById('updateBtnLabel');
const updateNoticeDot = document.getElementById('updateNoticeDot');

const footerYtdlpVer = document.getElementById('footerYtdlpVer');
const footerAppVer = document.getElementById('footerAppVer');

const updateModalOverlay = document.getElementById('updateModalOverlay');
const closeUpdateModalBtn = document.getElementById('closeUpdateModalBtn');
const dismissModalBtn = document.getElementById('dismissModalBtn');
const recheckUpdatesBtn = document.getElementById('recheckUpdatesBtn');
const recheckIcon = document.getElementById('recheckIcon');

const ytdlpStatusBadge = document.getElementById('ytdlpStatusBadge');
const modalYtdlpInstalled = document.getElementById('modalYtdlpInstalled');
const modalYtdlpLatest = document.getElementById('modalYtdlpLatest');
const ytdlpProgressBox = document.getElementById('ytdlpProgressBox');
const ytdlpProgressFill = document.getElementById('ytdlpProgressFill');
const ytdlpProgressMsg = document.getElementById('ytdlpProgressMsg');
const runYtdlpUpdateBtn = document.getElementById('runYtdlpUpdateBtn');
const restartAppBtn = document.getElementById('restartAppBtn');

const appStatusBadge = document.getElementById('appStatusBadge');
const modalAppInstalled = document.getElementById('modalAppInstalled');
const modalAppLatest = document.getElementById('modalAppLatest');
const appNotesBox = document.getElementById('appNotesBox');
const appNotesContent = document.getElementById('appNotesContent');
const appProgressBox = document.getElementById('appProgressBox');
const appProgressFill = document.getElementById('appProgressFill');
const appProgressMsg = document.getElementById('appProgressMsg');
const runAppUpdateBtn = document.getElementById('runAppUpdateBtn');

let lastCheckedUpdates = null;

// ================= LIQUID GLASS PHYSICS & ANIMATIONS =================

// 1. Jelly Elastic Glider Positioning
function updateGlider(gliderEl, targetBtn) {
  if (!gliderEl || !targetBtn) return;
  const parent = targetBtn.parentElement;
  if (!parent) return;
  const pRect = parent.getBoundingClientRect();
  const bRect = targetBtn.getBoundingClientRect();
  
  if (bRect.width === 0 && bRect.height === 0) return;

  const left = bRect.left - pRect.left;
  const width = bRect.width;

  gliderEl.style.transform = `translateX(${left}px)`;
  gliderEl.style.width = `${width}px`;
}

// 2. Interactive Liquid Glass Specular Glare Tracking (RAF Throttled + Cached Rect)
function setupLiquidTilt() {
  const tiltPanels = document.querySelectorAll('.glass-panel[data-tilt="true"]');
  
  tiltPanels.forEach(panel => {
    let cachedRect = null;
    let rafId = null;

    panel.addEventListener('mouseenter', () => {
      cachedRect = panel.getBoundingClientRect();
    });

    panel.addEventListener('mousemove', (e) => {
      if (!cachedRect) cachedRect = panel.getBoundingClientRect();
      const clientX = e.clientX;
      const clientY = e.clientY;
      if (rafId) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        const x = clientX - cachedRect.left;
        const y = clientY - cachedRect.top;
        panel.style.setProperty('--mouse-x', `${x}px`);
        panel.style.setProperty('--mouse-y', `${y}px`);
        panel.style.setProperty('--specular-opacity', '1');
      });
    });

    panel.addEventListener('mouseleave', () => {
      if (rafId) cancelAnimationFrame(rafId);
      cachedRect = null;
      panel.style.setProperty('--specular-opacity', '0');
    });
  });

  window.addEventListener('resize', () => {
    tiltPanels.forEach(panel => {
      panel.style.setProperty('--specular-opacity', '0');
    });
  });
}

// Pause heavy CSS keyframe animations when window loses focus or is minimized
function handleWindowFocusBlur() {
  const isInactive = document.hidden || !document.hasFocus();
  if (isInactive) {
    document.body.classList.add('window-inactive');
  } else {
    document.body.classList.remove('window-inactive');
  }
}
window.addEventListener('blur', handleWindowFocusBlur);
window.addEventListener('focus', handleWindowFocusBlur);
document.addEventListener('visibilitychange', handleWindowFocusBlur);

// 3. Viscous Fluid Click Ripple
function createLiquidRipple(e, target) {
  const rect = target.getBoundingClientRect();
  const ripple = document.createElement('span');
  ripple.className = 'liquid-ripple';
  
  const size = Math.max(rect.width, rect.height) * 2;
  const x = e.clientX - rect.left - size / 2;
  const y = e.clientY - rect.top - size / 2;
  
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${x}px`;
  ripple.style.top = `${y}px`;
  
  target.appendChild(ripple);
  setTimeout(() => ripple.remove(), 700);
}

document.addEventListener('click', (e) => {
  const target = e.target.closest('.glass-btn-primary, .tab-btn, .format-tab-btn, .audio-btn, .quality-card');
  if (target) {
    createLiquidRipple(e, target);
  }
});

// ================= USER SETTINGS CONTROLLER =================
async function loadUserSettings() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const s = await window.pywebview.api.get_settings();
    if (!s) return;
    if (s.download_dir && destPathText) {
      destPathText.textContent = s.download_dir;
    }
    if (s.theme) {
      docEl.setAttribute('data-theme', s.theme);
      if (themeIcon) themeIcon.textContent = s.theme === 'light' ? '🌙' : '☀️';
      if (themeLabel) themeLabel.textContent = s.theme === 'light' ? 'Dark Mode' : 'Light Mode';
      if (themeToggleBtn) themeToggleBtn.setAttribute('title', s.theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode');
    }
    if (typeof s.turbo_enabled === 'boolean' && turboCheck) {
      turboCheck.checked = s.turbo_enabled;
      const container = document.getElementById('turboToggleContainer');
      if (container) {
        if (s.turbo_enabled) container.classList.add('active');
        else container.classList.remove('active');
      }
    }
    if (embedMetaCheck && typeof s.embed_metadata === 'boolean') {
      embedMetaCheck.checked = s.embed_metadata;
    }
    if (embedSubsCheck && typeof s.embed_subtitles === 'boolean') {
      embedSubsCheck.checked = s.embed_subtitles;
    }
    autoCookiesEnabled = s.auto_cookies !== false;
    updateCookieBrowserUI(s.cookie_browser);
  } catch (e) {
    console.warn("Failed to load settings:", e);
  }
}

// Initialize physics on load
window.addEventListener('DOMContentLoaded', () => {
  setupLiquidTilt();
  updateDownloadButtonState();
  setTimeout(() => {
    updateGlider(tabGlider, tabSingleBtn);
    updateGlider(formatGlider, typeVideoBtn);
  }, 100);
});

// Bridge settlement handler
window.addEventListener('pywebviewready', async () => {
  try {
    await loadUserSettings();
  } catch (e) {}

  try {
    const cookieStatus = await window.pywebview.api.check_cookies();
    if (cookieStatus && cookieStatus.active) {
      updateCookieBrowserUI(cookieStatus.source);
    }
  } catch (e) {
    console.warn("Error checking cookies:", e);
  }

  try {
    await loadInstalledVersions();
  } catch (e) {
    console.warn("Error loading versions:", e);
  }

  try {
    await updateHistoryCount();
  } catch (e) {}

  try {
    window.on_queue_update(await window.pywebview.api.get_queue());
  } catch (e) {
    console.warn("Error loading queue:", e);
  }

  setTimeout(() => {
    checkClipboardUrl();
  }, 600);

  // Silently check for updates in background 3 seconds after complete settlement
  setTimeout(() => {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.check_updates_async) {
      window.pywebview.api.check_updates_async();
    }
  }, 3000);
});

// Update gliders when window is resized
window.addEventListener('resize', () => {
  const activeTab = currentMode === 'single' ? tabSingleBtn : tabBulkBtn;
  if (tabGlider && activeTab) updateGlider(tabGlider, activeTab);
  if (formatGlider && previewCard && previewCard.classList.contains('show')) {
    const activeFormat = selectedMediaType === 'video' ? typeVideoBtn : typeAudioBtn;
    if (activeFormat) updateGlider(formatGlider, activeFormat);
  }
});

// Theme Switching
themeToggleBtn.addEventListener('click', async () => {
  const current = docEl.getAttribute('data-theme');
  const newTheme = current === 'light' ? 'dark' : 'light';
  docEl.setAttribute('data-theme', newTheme);
  if (themeIcon) themeIcon.textContent = newTheme === 'light' ? '🌙' : '☀️';
  if (themeLabel) themeLabel.textContent = newTheme === 'light' ? 'Dark Mode' : 'Light Mode';
  themeToggleBtn.setAttribute('title', newTheme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode');
  if (window.pywebview && window.pywebview.api) {
    try {
      await window.pywebview.api.save_settings({ theme: newTheme });
    } catch (e) {}
  }
});

// Tabs Switching
tabSingleBtn.addEventListener('click', () => {
  currentMode = 'single';
  tabSingleBtn.classList.add('active');
  tabBulkBtn.classList.remove('active');
  updateGlider(tabGlider, tabSingleBtn);
  singleSection.style.display = 'flex';
  bulkSection.style.display = 'none';
  updateDownloadButtonState();
});

tabBulkBtn.addEventListener('click', () => {
  currentMode = 'bulk';
  tabBulkBtn.classList.add('active');
  tabSingleBtn.classList.remove('active');
  updateGlider(tabGlider, tabBulkBtn);
  singleSection.style.display = 'none';
  bulkSection.style.display = 'flex';
  updateDownloadButtonState();
});

// Keyboard Ergonomics: Enter in single URL input triggers Analyze
singleUrlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    analyzeBtn.click();
  }
});

// Pasting a link into the box analyzes it straight away
function looksLikeUrl(text) {
  return /^https?:\/\/\S+$/i.test((text || '').trim());
}

singleUrlInput.addEventListener('paste', (e) => {
  const cd = e.clipboardData || window.clipboardData;
  const text = cd ? cd.getData('text') : '';
  if (!looksLikeUrl(text)) return;
  e.preventDefault();
  singleUrlInput.value = text.trim();
  if (!analyzeBtn.disabled) analyzeBtn.click();
});

// Ctrl+V anywhere in the window (outside a text box) pastes and analyzes the link
document.addEventListener('keydown', (e) => {
  if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== 'v') return;
  const el = document.activeElement;
  if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return;
  if (currentMode !== 'single') return;
  e.preventDefault();
  pasteBtn.click();
});

// Drag a link from the browser onto the window to analyze it
const dropOverlay = document.getElementById('dropOverlay');
let dragDepth = 0;
function dragHasLink(e) {
  const types = Array.from((e.dataTransfer && e.dataTransfer.types) || []);
  return types.includes('text/uri-list') || types.includes('text/plain');
}
window.addEventListener('dragenter', (e) => {
  if (!dragHasLink(e)) return;
  e.preventDefault();
  dragDepth++;
  if (dropOverlay) dropOverlay.classList.add('show');
});
window.addEventListener('dragover', (e) => {
  if (dragHasLink(e)) e.preventDefault();
});
window.addEventListener('dragleave', () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth && dropOverlay) dropOverlay.classList.remove('show');
});
window.addEventListener('drop', (e) => {
  dragDepth = 0;
  if (dropOverlay) dropOverlay.classList.remove('show');
  const dt = e.dataTransfer;
  if (!dt) return;
  const raw = dt.getData('text/uri-list') || dt.getData('text/plain') || '';
  const url = raw.split(/\r?\n/).map(l => l.trim()).find(l => l && !l.startsWith('#')) || '';
  if (!looksLikeUrl(url)) return;
  e.preventDefault();
  if (currentMode === 'single') {
    singleUrlInput.value = url;
    if (!analyzeBtn.disabled) analyzeBtn.click();
  } else {
    bulkTextarea.value = (bulkTextarea.value.trim() + '\n' + url).trim();
  }
});

// Paste Buttons with Smart Auto-Analyze
pasteBtn.addEventListener('click', async () => {
  let text = '';
  if (window.pywebview && window.pywebview.api) {
    try {
      text = await window.pywebview.api.get_clipboard_text();
    } catch (e) {}
  }
  if (!text && navigator.clipboard && navigator.clipboard.readText) {
    try {
      text = await navigator.clipboard.readText();
    } catch (e) {}
  }
  if (text && text.trim()) {
    const clean = text.trim();
    singleUrlInput.value = clean;
    if (clean.startsWith('http://') || clean.startsWith('https://')) {
      analyzeBtn.click();
    }
  }
});

bulkPasteBtn.addEventListener('click', async () => {
  let text = '';
  if (window.pywebview && window.pywebview.api) {
    try {
      text = await window.pywebview.api.get_clipboard_text();
    } catch (e) {}
  }
  if (!text && navigator.clipboard && navigator.clipboard.readText) {
    try {
      text = await navigator.clipboard.readText();
    } catch (e) {}
  }
  if (text && text.trim()) {
    bulkTextarea.value = text.trim();
  }
});

// Browse & Open Output Folder
browseDestBtn.addEventListener('click', async () => {
  if (!window.pywebview || !window.pywebview.api) return;
  const folder = await window.pywebview.api.select_directory();
  if (folder) {
    destPathText.textContent = folder;
    await window.pywebview.api.save_settings({ download_dir: folder });
  }
});

openDestBtn.addEventListener('click', async () => {
  if (!window.pywebview || !window.pywebview.api) return;
  await window.pywebview.api.open_directory(destPathText.textContent);
});

// Format Type Selection (Video vs Audio)
function selectMediaType(type) {
  selectedMediaType = type;
  if (type === 'video') {
    typeVideoBtn.classList.add('active');
    typeAudioBtn.classList.remove('active');
    updateGlider(formatGlider, typeVideoBtn);
    videoResolutionsSection.style.display = 'block';
    audioQualitySection.style.display = 'none';
  } else {
    typeAudioBtn.classList.add('active');
    typeVideoBtn.classList.remove('active');
    updateGlider(formatGlider, typeAudioBtn);
    videoResolutionsSection.style.display = 'none';
    audioQualitySection.style.display = 'block';
  }
}
typeVideoBtn.addEventListener('click', () => selectMediaType('video'));
typeAudioBtn.addEventListener('click', () => selectMediaType('audio'));

// Audio Format Selection (MP3, M4A, WAV)
function selectAudioFormat(format) {
  selectedAudioQuality = format;
  audioMp3Btn.classList.toggle('selected', format === 'MP3');
  if (audioM4aBtn) audioM4aBtn.classList.toggle('selected', format === 'M4A');
  audioWavBtn.classList.toggle('selected', format === 'WAV');
}
audioMp3Btn.addEventListener('click', () => selectAudioFormat('MP3'));
if (audioM4aBtn) audioM4aBtn.addEventListener('click', () => selectAudioFormat('M4A'));
audioWavBtn.addEventListener('click', () => selectAudioFormat('WAV'));

// Checkbox Settings Persistence
if (embedSubsCheck) {
  embedSubsCheck.addEventListener('change', async () => {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.save_settings({ embed_subtitles: embedSubsCheck.checked });
    }
  });
}
if (embedMetaCheck) {
  embedMetaCheck.addEventListener('change', async () => {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.save_settings({ embed_metadata: embedMetaCheck.checked });
    }
  });
}

// Bulk Format Selector Buttons
function setBulkFormat(type, quality) {
  selectedMediaType = type;
  if (type === 'video') {
    if (bulkResCapWrapper) bulkResCapWrapper.style.display = 'flex';
    bulkTypeVideo.style.background = 'var(--accent-gradient)';
    bulkTypeVideo.style.color = '#fff';
    bulkTypeMp3.style.background = 'var(--glass-bg)';
    bulkTypeMp3.style.color = 'var(--text-main)';
    bulkTypeWav.style.background = 'var(--glass-bg)';
    bulkTypeWav.style.color = 'var(--text-main)';
  } else if (quality === 'MP3') {
    selectedAudioQuality = 'MP3';
    if (bulkResCapWrapper) bulkResCapWrapper.style.display = 'none';
    bulkTypeMp3.style.background = 'var(--accent-gradient)';
    bulkTypeMp3.style.color = '#fff';
    bulkTypeVideo.style.background = 'var(--glass-bg)';
    bulkTypeVideo.style.color = 'var(--text-main)';
    bulkTypeWav.style.background = 'var(--glass-bg)';
    bulkTypeWav.style.color = 'var(--text-main)';
  } else {
    selectedAudioQuality = 'WAV';
    if (bulkResCapWrapper) bulkResCapWrapper.style.display = 'none';
    bulkTypeWav.style.background = 'var(--accent-gradient)';
    bulkTypeWav.style.color = '#fff';
    bulkTypeVideo.style.background = 'var(--glass-bg)';
    bulkTypeVideo.style.color = 'var(--text-main)';
    bulkTypeMp3.style.background = 'var(--glass-bg)';
    bulkTypeMp3.style.color = 'var(--text-main)';
  }
}
bulkTypeVideo.addEventListener('click', () => setBulkFormat('video', 'best'));
bulkTypeMp3.addEventListener('click', () => setBulkFormat('audio', 'MP3'));
bulkTypeWav.addEventListener('click', () => setBulkFormat('audio', 'WAV'));

// Analyze Single URL
analyzeBtn.addEventListener('click', async () => {
  const url = singleUrlInput.value.trim();
  if (!url) {
    showToast("Please paste a video or media link first.", "error");
    return;
  }

  clearFinishedDownload();
  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<span>⏳</span> Analyzing...';
  previewCard.classList.remove('show');

  try {
    const res = await window.pywebview.api.analyze_url(url);
    if (res.error) {
      showToast("Analysis Error: " + res.error, "error");
    } else {
      currentSingleData = res;
      displaySinglePreview(res);
    }
  } catch (err) {
    showToast("Failed to analyze: " + err, "error");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = '<span>🔍</span> Analyze Link';
  }
});

function displaySinglePreview(data) {
  previewTitle.textContent = data.title || "Video";
  previewChannel.textContent = data.channel || data.platform || "";
  previewPlatform.textContent = data.platform || "Video";
  previewDuration.textContent = data.duration || "";
  
  if (data.thumbnail) {
    previewThumb.src = data.thumbnail;
    previewThumb.style.display = 'block';
  } else {
    previewThumb.style.display = 'none';
  }

  // Update audio estimated sizes
  if (audioMp3Size) {
    audioMp3Size.textContent = data.audio_mp3_size ? `${data.audio_mp3_size} • High quality` : '320 kbps High quality';
  }
  if (audioM4aSize) {
    audioM4aSize.textContent = data.audio_m4a_size ? `${data.audio_m4a_size} • Native AAC` : 'Native AAC stream';
  }
  if (audioWavSize) {
    audioWavSize.textContent = data.audio_wav_size ? `${data.audio_wav_size} • Lossless PCM` : 'Studio Lossless PCM';
  }

  // Populate resolutions grid
  resolutionsGrid.innerHTML = '';
  const resolutions = data.resolutions || [];
  
  if (resolutions.length === 0) {
    const card = document.createElement('div');
    card.className = 'quality-card selected';
    card.innerHTML = `<div class="quality-label">Best Quality</div><div class="quality-sub">Original Source</div>`;
    resolutionsGrid.appendChild(card);
    selectedVideoQuality = 'best';
  } else {
    resolutions.forEach((res, idx) => {
      const card = document.createElement('div');
      card.className = `quality-card ${idx === 0 ? 'selected' : ''}`;
      card.dataset.height = res.height;
      const sizeInfo = res.filesize_str ? `${res.filesize_str} • MP4` : 'MP4 Video';
      card.innerHTML = `
        <div class="quality-label">${escapeHtml(res.label)}</div>
        <div class="quality-sub">${escapeHtml(sizeInfo)}</div>
      `;
      card.addEventListener('click', () => {
        document.querySelectorAll('.quality-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedVideoQuality = res.height;
      });
      resolutionsGrid.appendChild(card);
    });
    selectedVideoQuality = resolutions[0].height;
  }

  previewCard.classList.add('show');
  selectMediaType('video');
  setTimeout(() => {
    updateGlider(formatGlider, typeVideoBtn);
  }, 40);
  updateDownloadButtonState();
}

// Analyze Bulk / Playlist
analyzeBulkBtn.addEventListener('click', async () => {
  const text = bulkTextarea.value.trim();
  if (!text) {
    showToast("Please enter a playlist URL or list of video links.", "error");
    return;
  }

  analyzeBulkBtn.disabled = true;
  analyzeBulkBtn.innerHTML = '<span>⏳</span> Analyzing Queue...';

  try {
    const res = await window.pywebview.api.analyze_bulk(text);
    if (res.error) {
      showToast("Error: " + res.error, "error");
    } else {
      currentBulkData = res;
      displayBulkQueue(res);
    }
  } catch (err) {
    showToast("Bulk analysis failed: " + err, "error");
  } finally {
    analyzeBulkBtn.disabled = false;
    analyzeBulkBtn.innerHTML = '<span>🔍</span> Analyze Playlist / Links';
  }
});

function updateBulkSelectionSummary() {
  if (!currentBulkData || !currentBulkData.items) return;
  const total = currentBulkData.items.length;
  const selected = currentBulkData.items.filter(it => it._selected !== false).length;
  bulkSummaryText.textContent = `Queue: ${selected}/${total} selected`;
  if (bulkSelectAllBtn) {
    bulkSelectAllBtn.textContent = selected === total ? "Deselect All" : "Select All";
  }
  updateDownloadButtonState();
}

if (bulkSelectAllBtn) {
  bulkSelectAllBtn.addEventListener('click', () => {
    if (!currentBulkData || !currentBulkData.items) return;
    const allSelected = currentBulkData.items.every(it => it._selected !== false);
    const target = !allSelected;
    currentBulkData.items.forEach((it, idx) => {
      it._selected = target;
      const chk = document.querySelector(`.bulk-item-check[data-idx="${idx}"]`);
      if (chk) chk.checked = target;
    });
    updateBulkSelectionSummary();
  });
}

function displayBulkQueue(data) {
  bulkItemsList.innerHTML = '';

  data.items.forEach((item, idx) => {
    item._selected = true;
    const row = document.createElement('div');
    row.className = 'bulk-item-row';
    row.id = `bulk-item-${idx}`;
    row.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px; flex: 1; overflow: hidden;">
        <input type="checkbox" class="bulk-item-check" data-idx="${idx}" checked style="cursor: pointer; width: 15px; height: 15px; accent-color: var(--accent-cyan); flex-shrink: 0;" />
        <span style="color: var(--text-muted); font-size: 11px;">#${idx+1}</span>
        <span class="bulk-item-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</span>
      </div>
      <div style="display: flex; align-items: center; gap: 8px; flex-shrink: 0;">
        <span class="plat-chip" style="font-size: 11px;">${escapeHtml(item.platform || 'Video')}</span>
        <span class="bulk-item-status" id="bulk-status-${idx}">Pending</span>
      </div>
    `;
    const chk = row.querySelector('.bulk-item-check');
    chk.addEventListener('change', (e) => {
      item._selected = e.target.checked;
      updateBulkSelectionSummary();
    });
    bulkItemsList.appendChild(row);
  });

  updateBulkSelectionSummary();
  setBulkFormat('video', 'best');
  bulkOptionsCard.style.display = 'flex';
  updateDownloadButtonState();
}

function updateDownloadButtonState() {
  if (activeQueueJob) {
    const hasSelection = currentMode === 'single'
      ? !!currentSingleData
      : !!(currentBulkData && currentBulkData.items && currentBulkData.items.some(it => it._selected !== false));
    startDownloadBtn.disabled = !hasSelection;
    downloadBtnText.textContent = "Add to Queue";
    return;
  }
  if (isDownloading) {
    startDownloadBtn.disabled = true;
    return;
  }
  if (currentMode === 'single') {
    startDownloadBtn.disabled = !currentSingleData;
    downloadBtnText.textContent = !currentSingleData
      ? "Paste a link above to start"
      : (turboCheck.checked ? "Start Turbo Download (8x)" : "Start Download");
  } else {
    const selectedCount = currentBulkData && currentBulkData.items ? currentBulkData.items.filter(it => it._selected !== false).length : 0;
    startDownloadBtn.disabled = selectedCount === 0;
    downloadBtnText.textContent = selectedCount === 0
      ? "Add links above, then press Analyze"
      : (turboCheck.checked
        ? `Start Turbo Queue Download (${selectedCount} items)`
        : `Start Queue Download (${selectedCount} items)`);
  }
  const btnIcon = document.getElementById('downloadBtnIcon');
  if (btnIcon) btnIcon.style.display = startDownloadBtn.disabled ? 'none' : '';
}

turboCheck.addEventListener('change', async () => {
  const container = document.getElementById('turboToggleContainer');
  if (turboCheck.checked) {
    container.classList.add('active');
  } else {
    container.classList.remove('active');
  }
  updateDownloadButtonState();
  if (window.pywebview && window.pywebview.api) {
    try {
      await window.pywebview.api.save_settings({ turbo_enabled: turboCheck.checked });
    } catch (e) {}
  }
});

// Pause & Cancel Handlers
async function togglePause() {
  if (!isDownloading || !window.pywebview || !window.pywebview.api) return;
  if (!isPaused) {
    await window.pywebview.api.pause_download();
    isPaused = true;
    pauseBtnIcon.textContent = '▶';
    pauseBtnText.textContent = 'Resume';
    pauseDownloadBtn.style.color = '#4ade80';
    pauseDownloadBtn.style.borderColor = 'rgba(74, 222, 128, 0.45)';
    miniPauseBtn.textContent = '▶';
    progressFill.classList.add('paused');
    progressSpeed.textContent = 'Paused';
    progressEta.textContent = 'Paused';
    progressTitle.textContent = 'Download Paused';
  } else {
    await window.pywebview.api.resume_download();
    isPaused = false;
    pauseBtnIcon.textContent = '⏸';
    pauseBtnText.textContent = 'Pause';
    pauseDownloadBtn.style.color = '';
    pauseDownloadBtn.style.borderColor = '';
    miniPauseBtn.textContent = '⏸';
    progressFill.classList.remove('paused');
    progressTitle.textContent = 'Downloading...';
  }
}

async function triggerCancel() {
  if (!isDownloading || !window.pywebview || !window.pywebview.api) return;
  await window.pywebview.api.cancel_download();
  isDownloading = false;
  isPaused = false;
  progressFill.classList.remove('paused');
  progressTitle.textContent = 'Download Cancelled ✗';
  progressSpeed.textContent = '-- MB/s';
  progressEta.textContent = 'ETA: --';
  downloadControlsRow.style.display = 'none';
  startDownloadBtn.style.display = 'inline-flex';
  miniPauseBtn.style.display = 'none';
  miniCancelBtn.style.display = 'none';
  updateDownloadButtonState();
}

pauseDownloadBtn.addEventListener('click', togglePause);
miniPauseBtn.addEventListener('click', togglePause);
cancelDownloadBtn.addEventListener('click', triggerCancel);
miniCancelBtn.addEventListener('click', triggerCancel);

// Download Execution
startDownloadBtn.addEventListener('click', async () => {
  if (activeQueueJob) {
    await addSelectionToQueue();
    return;
  }
  if (isDownloading) return;
  const isTurbo = turboCheck.checked;
  const outDir = destPathText.textContent.trim();

  isDownloading = true;
  isPaused = false;
  startDownloadBtn.style.display = 'none';
  downloadControlsRow.style.display = 'flex';
  miniPauseBtn.style.display = 'inline-flex';
  miniCancelBtn.style.display = 'inline-flex';
  pauseBtnIcon.textContent = '⏸';
  pauseBtnText.textContent = 'Pause';
  pauseDownloadBtn.style.color = '';
  pauseDownloadBtn.style.borderColor = '';
  miniPauseBtn.textContent = '⏸';

  progressCard.classList.add('show');
  resetProgress();

  if (currentMode === 'single') {
    if (!currentSingleData) {
      showToast("Please enter and analyze a video link first.", "error");
      isDownloading = false;
      downloadControlsRow.style.display = 'none';
      startDownloadBtn.style.display = '';
      return;
    }
    const url = currentSingleData.webpage_url || singleUrlInput.value.trim();
    const quality = selectedMediaType === 'video' ? selectedVideoQuality : selectedAudioQuality;
    const clipStart = clipStartInput ? clipStartInput.value.trim() : "";
    const clipEnd = clipEndInput ? clipEndInput.value.trim() : "";
    const embedSubs = embedSubsCheck ? embedSubsCheck.checked : false;
    const embedMeta = embedMetaCheck ? embedMetaCheck.checked : false;

    progressTitle.textContent = `Downloading: ${currentSingleData.title}`;

    try {
      const res = await window.pywebview.api.download_single(
        url,
        selectedMediaType,
        quality,
        outDir,
        isTurbo,
        clipStart,
        clipEnd,
        embedSubs,
        embedMeta
      );
      if (res && res.cancelled) {
        progressTitle.textContent = "Download Cancelled ✗";
      } else if (res && res.error) {
        showToast("Download Failed: " + res.error, "error");
        progressTitle.textContent = "Download Error";
      } else {
        progressTitle.textContent = "Download Complete ✓";
        progressFill.style.width = '100%';
        progressPercent.textContent = '100%';
        showFinishedStats(res && res.file_size);

        lastDownloadedFilePath = (res && res.file_path) ? res.file_path : null;

        try {
          window.pywebview.api.play_completion_sound();
        } catch (e) {}
        showToast("Download completed successfully! Paste your next link any time.", "success", 4000);
        // Ready for the next link straight away: no need to press New.
        lastDismissedClipboardUrl = url; // don't offer the link we just downloaded again
        singleUrlInput.value = '';
        singleUrlInput.focus();

        try {
          const histItem = {
            id: Date.now().toString(),
            title: currentSingleData.title || "Downloaded Media",
            platform: currentSingleData.platform || "Online Video",
            url: url,
            file_path: lastDownloadedFilePath,
            format: selectedMediaType === 'audio' ? selectedAudioQuality : `${selectedVideoQuality}p MP4`,
            duration: currentSingleData.duration || "--",
            thumbnail: currentSingleData.thumbnail || "",
            size: progressSize ? progressSize.textContent.split('/')[0].trim() : "",
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          };
          await window.pywebview.api.add_history(histItem);
          updateHistoryCount();
        } catch (e) {}

        if (lastDownloadedFilePath && postDownloadBar) {
          if (openFileLabel) {
            openFileLabel.textContent = selectedMediaType === 'audio' ? 'Play Audio' : 'Play Video';
          }
          if (openFileIcon) {
            openFileIcon.textContent = selectedMediaType === 'audio' ? '🎵' : '🎬';
          }
          postDownloadBar.style.display = 'flex';
        }
      }
    } catch (err) {
      if (isDownloading) {
        showToast("Error: " + err, "error");
        progressTitle.textContent = "Error";
      }
    } finally {
      isDownloading = false;
      isPaused = false;
      downloadControlsRow.style.display = 'none';
      if (!lastDownloadedFilePath) {
        startDownloadBtn.style.display = 'inline-flex';
      } else {
        startDownloadBtn.style.display = 'none';
      }
      miniPauseBtn.style.display = 'none';
      miniCancelBtn.style.display = 'none';
      progressFill.classList.remove('paused');
      updateDownloadButtonState();
      syncQueueControls();
    }
  } else {
    // Bulk queue download
    const itemsToDownload = currentBulkData && currentBulkData.items
      ? currentBulkData.items
          .map((item, origIdx) => ({ ...item, _origIdx: origIdx }))
          .filter(item => item._selected !== false)
      : [];

    if (itemsToDownload.length === 0) {
      showToast("No queue items selected for download.", "error");
      isDownloading = false;
      downloadControlsRow.style.display = 'none';
      startDownloadBtn.style.display = '';
      return;
    }

    const cap = bulkResCapSelect ? bulkResCapSelect.value : 'best';
    const quality = selectedMediaType === 'video' ? cap : selectedAudioQuality;
    progressTitle.textContent = `Processing Queue (0 / ${itemsToDownload.length})`;

    try {
      const res = await window.pywebview.api.download_bulk(
        itemsToDownload,
        selectedMediaType,
        quality,
        outDir,
        isTurbo
      );
      if (res && res.cancelled) {
        progressTitle.textContent = "Queue Cancelled ✗";
      } else if (res && res.error) {
        showToast("Bulk Download Error: " + res.error, "error");
      } else {
        progressTitle.textContent = `Queue Complete: ${res.successful}/${res.total} downloaded`;
        progressFill.style.width = '100%';
        progressPercent.textContent = '100%';
        showFinishedStats(null);
        showToast(`Queue complete: ${res.successful}/${res.total} downloaded`, "success", 4000);
        updateHistoryCount();
      }
    } catch (err) {
      if (isDownloading) {
        showToast("Bulk download error: " + err, "error");
      }
    } finally {
      isDownloading = false;
      isPaused = false;
      downloadControlsRow.style.display = 'none';
      startDownloadBtn.style.display = 'inline-flex';
      miniPauseBtn.style.display = 'none';
      miniCancelBtn.style.display = 'none';
      progressFill.classList.remove('paused');
      updateDownloadButtonState();
      syncQueueControls();
    }
  }
});

// ================= BACKGROUND DOWNLOAD QUEUE =================
const queuePanel = document.getElementById('queuePanel');
const queueSummary = document.getElementById('queueSummary');
const queueList = document.getElementById('queueList');
const queueClearBtn = document.getElementById('queueClearBtn');
const queueStatusLabels = {
  queued: 'Queued', downloading: 'Downloading...', done: 'Done ✓', failed: 'Failed ✗', cancelled: 'Cancelled ✗'
};
const seenQueueStatus = new Map();

function resetPauseControls() {
  isPaused = false;
  pauseBtnIcon.textContent = '⏸';
  pauseBtnText.textContent = 'Pause';
  pauseDownloadBtn.style.color = '';
  pauseDownloadBtn.style.borderColor = '';
  miniPauseBtn.textContent = '⏸';
  progressFill.classList.remove('paused');
}

// Download controls are shared, so a queue job takes them over while it runs.
function syncQueueControls() {
  if (!activeQueueJob) return;
  isDownloading = true;
  progressCard.classList.add('show');
  downloadControlsRow.style.display = 'flex';
  miniPauseBtn.style.display = 'inline-flex';
  miniCancelBtn.style.display = 'inline-flex';
  startDownloadBtn.style.display = 'inline-flex';
  updateDownloadButtonState();
}

function releaseQueueControls() {
  isDownloading = false;
  resetPauseControls();
  downloadControlsRow.style.display = 'none';
  miniPauseBtn.style.display = 'none';
  miniCancelBtn.style.display = 'none';
  startDownloadBtn.style.display = 'inline-flex';
  updateDownloadButtonState();
}

function renderQueue(jobs) {
  const finished = jobs.filter(j => ['done', 'failed', 'cancelled'].includes(j.status)).length;
  queuePanel.style.display = jobs.length ? 'block' : 'none';
  queueSummary.textContent = `Queue: ${jobs.length - finished} active, ${finished} finished`;
  queueClearBtn.style.display = finished ? 'inline-flex' : 'none';
  queueList.innerHTML = '';
  jobs.forEach((job) => {
    const row = document.createElement('div');
    row.className = 'bulk-item-row';
    const title = job.title || job.url;
    const removable = job.status !== 'downloading';
    row.innerHTML = `
      <span class="bulk-item-title" title="${escapeHtml(job.error || title)}">${escapeHtml(title)}</span>
      <div class="queue-job-actions">
        <span class="bulk-item-status ${escapeHtml(job.status)}">${escapeHtml(queueStatusLabels[job.status] || job.status)}</span>
        ${removable ? '<button class="history-btn-mini delete" title="Remove from queue">✕</button>' : ''}
      </div>
    `;
    if (removable) {
      row.querySelector('button').addEventListener('click', () => {
        window.pywebview.api.remove_queue_job(job.id);
      });
    }
    queueList.appendChild(row);
  });
}

function announceFinishedJobs(jobs) {
  jobs.forEach((job) => {
    const previous = seenQueueStatus.get(job.id);
    seenQueueStatus.set(job.id, job.status);
    if (!previous && job.status === 'queued') {
      showToast(`Added to queue: ${job.title || job.url}`, 'info', 2500);
    } else if (previous !== 'done' && job.status === 'done') {
      showToast(`Downloaded: ${job.title || job.url}`, 'success', 4000);
      updateHistoryCount();
      try { window.pywebview.api.play_completion_sound(); } catch (e) {}
    } else if (previous !== 'failed' && job.status === 'failed') {
      showToast(`Download failed: ${job.error}`, 'error');
    }
  });
}

window.on_queue_update = function(jobs) {
  const previous = activeQueueJob;
  activeQueueJob = jobs.find(j => j.status === 'downloading') || null;
  if (activeQueueJob) {
    if (!previous || previous.id !== activeQueueJob.id) {
      resetProgress();
      resetPauseControls();
      if (postDownloadBar) postDownloadBar.style.display = 'none';
    }
    progressTitle.textContent = `Downloading: ${activeQueueJob.title || activeQueueJob.url}`;
    syncQueueControls();
  } else if (previous) {
    releaseQueueControls();
    const last = jobs.find(j => j.id === previous.id);
    progressTitle.textContent = last && last.status === 'done' ? 'Download Complete ✓' : 'Ready';
    if (last && last.status === 'done') {
      progressFill.style.width = '100%';
      progressPercent.textContent = '100%';
      showFinishedStats(null);
    }
  }
  announceFinishedJobs(jobs);
  renderQueue(jobs);
};

async function addSelectionToQueue() {
  const api = window.pywebview.api;
  if (currentMode === 'single') {
    if (!currentSingleData) return;
    const quality = selectedMediaType === 'video' ? selectedVideoQuality : selectedAudioQuality;
    await api.enqueue_download(
      currentSingleData.webpage_url || singleUrlInput.value.trim(),
      selectedMediaType,
      quality,
      currentSingleData.title || '',
      {
        clip_start: clipStartInput ? clipStartInput.value.trim() : '',
        clip_end: clipEndInput ? clipEndInput.value.trim() : '',
        embed_subtitles: embedSubsCheck ? embedSubsCheck.checked : false,
        embed_metadata: embedMetaCheck ? embedMetaCheck.checked : false
      }
    );
    return;
  }
  const quality = selectedMediaType === 'video' ? (bulkResCapSelect ? bulkResCapSelect.value : 'best') : selectedAudioQuality;
  const items = currentBulkData && currentBulkData.items ? currentBulkData.items.filter(it => it._selected !== false) : [];
  for (const item of items) {
    await api.enqueue_download(item.url, selectedMediaType, quality, item.title || '');
  }
}

queueClearBtn.addEventListener('click', () => {
  window.pywebview.api.clear_finished_queue_jobs();
});

function formatBytes(bytes) {
  if (!bytes || bytes <= 0) return '';
  const mb = bytes / 1048576;
  return mb >= 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(1)} MB`;
}

// Replaces the last live numbers (often "Unknown B/s" and a partial size) with the result
function showFinishedStats(fileSize) {
  progressSpeed.textContent = 'Done ✓';
  progressEta.textContent = '';
  const exact = formatBytes(fileSize);
  if (exact) {
    progressSize.textContent = exact;
    return;
  }
  const total = (progressSize.textContent.split('/')[1] || '').trim();
  progressSize.textContent = total && !/^(0(\.0)? MB|Unknown)$/.test(total) ? total : '';
}

function resetProgress() {
  progressFill.style.width = '0%';
  progressPercent.textContent = '0%';
  progressSpeed.textContent = '-- MB/s';
  progressEta.textContent = 'ETA: --';
  progressSize.textContent = '0 MB / 0 MB';
}

// Global functions invoked from Python via webview.evaluate_js
window.update_progress = function(percent, speed, eta, downloaded, total, status) {
  // Progress arrives on its own thread and can land after the download has ended.
  if (!isDownloading && !activeQueueJob) return;
  progressFill.style.width = `${percent}%`;
  progressPercent.textContent = `${Math.round(percent)}%`;
  if (speed) progressSpeed.textContent = speed;
  if (eta) progressEta.textContent = `ETA: ${eta}`;
  if (downloaded && total) progressSize.textContent = `${downloaded} / ${total}`;
  if (status) progressTitle.textContent = status;
};

window.update_bulk_progress = function(idx, total, title, status) {
  progressTitle.textContent = `[${idx}/${total}] ${title}`;
  const statusEl = document.getElementById(`bulk-status-${idx - 1}`);
  if (statusEl) {
    if (status === 'downloading') {
      statusEl.textContent = 'Downloading...';
      statusEl.style.background = 'rgba(6, 182, 212, 0.25)';
      statusEl.style.color = '#22d3ee';
    } else if (status === 'finished') {
      statusEl.textContent = 'Done ✓';
      statusEl.style.background = 'rgba(74, 222, 128, 0.25)';
      statusEl.style.color = '#4ade80';
      updateHistoryCount();
    } else if (status === 'error') {
      statusEl.textContent = 'Failed ✗';
      statusEl.style.background = 'rgba(239, 68, 68, 0.25)';
      statusEl.style.color = '#f87171';
    } else if (status === 'cancelled') {
      statusEl.textContent = 'Cancelled ✗';
      statusEl.style.background = 'rgba(239, 68, 68, 0.25)';
      statusEl.style.color = '#f87171';
    }
  }
};

// ================= LIQUID GLASS TOAST SYSTEM =================
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `glass-toast toast-${type}`;
  
  const iconMap = {
    success: '✓',
    error: '✗',
    info: '⚡'
  };
  const icon = iconMap[type] || 'ℹ️';

  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    <span class="toast-close">✕</span>
  `;

  toast.querySelector('.toast-close').addEventListener('click', (e) => {
    e.stopPropagation();
    dismissToast(toast);
  });

  toast.addEventListener('click', () => dismissToast(toast));

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  if (duration > 0) {
    setTimeout(() => {
      dismissToast(toast);
    }, duration);
  }
}

function dismissToast(toast) {
  if (!toast || toast.classList.contains('hide')) return;
  toast.classList.remove('show');
  toast.classList.add('hide');
  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, 320);
}

// ================= ANTI-BOT & COOKIES CONTROLLER =================
function updateCookieBrowserUI(browser) {
  const b = (browser || 'none').toLowerCase();
  selectedCookieBrowser = b;
  const autoOnly = b === 'none' && autoCookiesEnabled;
  if (autoCookiesCheck) autoCookiesCheck.checked = autoCookiesEnabled;
  cookieBrowserBtns.forEach(btn => {
    if (btn.dataset.browser === b && !autoOnly) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  if (currentCookieBadge) {
    if (autoOnly) {
      currentCookieBadge.textContent = 'Automatic';
      currentCookieBadge.className = 'status-badge uptodate';
    } else if (b === 'none') {
      currentCookieBadge.textContent = 'Disabled';
      currentCookieBadge.className = 'status-badge';
    } else if (b === 'file') {
      currentCookieBadge.textContent = 'cookies.txt Active';
      currentCookieBadge.className = 'status-badge uptodate';
    } else {
      currentCookieBadge.textContent = `${b.charAt(0).toUpperCase() + b.slice(1)} Active`;
      currentCookieBadge.className = 'status-badge uptodate';
    }
  }

  if (cookiesLabel && cookiesBtn) {
    let label = 'Sign-in: Off';
    if (autoOnly) label = 'Sign-in: Auto';
    else if (b === 'file') label = 'Sign-in: cookies.txt';
    else if (b !== 'none') label = `Sign-in: ${b.charAt(0).toUpperCase() + b.slice(1)}`;
    cookiesLabel.textContent = label;
    const dot = document.getElementById('cookiesDot');
    if (dot) dot.classList.toggle('on', b !== 'none' || autoOnly);
  }
}

function openCookiesModal() {
  if (cookiesModalOverlay) cookiesModalOverlay.classList.add('show');
}

function closeCookiesModal() {
  if (cookiesModalOverlay) cookiesModalOverlay.classList.remove('show');
}

if (cookiesBtn) cookiesBtn.addEventListener('click', openCookiesModal);
if (closeCookiesModalBtn) closeCookiesModalBtn.addEventListener('click', closeCookiesModal);
if (dismissCookiesBtn) dismissCookiesBtn.addEventListener('click', closeCookiesModal);
if (cookiesModalOverlay) {
  cookiesModalOverlay.addEventListener('click', (e) => {
    if (e.target === cookiesModalOverlay) closeCookiesModal();
  });
}

cookieBrowserBtns.forEach(btn => {
  btn.addEventListener('click', async () => {
    const browser = btn.dataset.browser;
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.set_cookie_browser(browser);
    }
    if (browser === 'none') autoCookiesEnabled = false;
    updateCookieBrowserUI(browser);
    showToast(browser === 'none' ? 'Anti-bot cookies disabled' : `Cookies auto-detection set to ${browser}`, 'success');
  });
});

const openExtensionFolderBtn = document.getElementById('openExtensionFolderBtn');
if (openExtensionFolderBtn) {
  openExtensionFolderBtn.addEventListener('click', async () => {
    const res = await window.pywebview.api.open_extension_folder();
    if (res && res.error) showToast(res.error, 'error');
  });
}

if (autoCookiesCheck) {
  autoCookiesCheck.addEventListener('change', async () => {
    autoCookiesEnabled = autoCookiesCheck.checked;
    await window.pywebview.api.set_auto_cookies(autoCookiesEnabled);
    updateCookieBrowserUI(selectedCookieBrowser);
  });
}

if (importCookiesFileBtn) {
  importCookiesFileBtn.addEventListener('click', async () => {
    if (!window.pywebview || !window.pywebview.api) return;
    const res = await window.pywebview.api.import_cookies();
    if (res && res.success) {
      updateCookieBrowserUI('file');
      showToast("Anti-bot bypass cookies.txt imported successfully!", "success");
    } else if (res && res.error) {
      showToast("Notice: " + res.error, "error");
    }
  });
}

// ================= SYSTEM & UPDATE CONTROLLER =================

async function loadInstalledVersions() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const v = await window.pywebview.api.get_versions();
    if (v) {
      if (v.ytdlp_version && footerYtdlpVer) {
        footerYtdlpVer.textContent = `yt-dlp v${v.ytdlp_version}`;
        if (modalYtdlpInstalled) {
          modalYtdlpInstalled.textContent = `v${v.ytdlp_version}` + (v.ytdlp_is_custom ? ' (Updated)' : '');
        }
      }
      if (v.app_version && footerAppVer) {
        footerAppVer.textContent = `v${v.app_version}`;
        if (modalAppInstalled) {
          modalAppInstalled.textContent = `v${v.app_version}`;
        }
      }
    }
  } catch (err) {
    console.error("Failed to load versions:", err);
  }
}

function openUpdateModal() {
  if (updateModalOverlay) {
    updateModalOverlay.classList.add('show');
  }
}

function closeUpdateModal() {
  if (updateModalOverlay) {
    updateModalOverlay.classList.remove('show');
  }
}

if (closeUpdateModalBtn) closeUpdateModalBtn.addEventListener('click', closeUpdateModal);
if (dismissModalBtn) dismissModalBtn.addEventListener('click', closeUpdateModal);
if (updateModalOverlay) {
  updateModalOverlay.addEventListener('click', (e) => {
    if (e.target === updateModalOverlay) {
      closeUpdateModal();
    }
  });
}

function applyUpdateCheckResult(res, { openModal = false, silent = false } = {}) {
  if (!res) return;
  lastCheckedUpdates = res;

  // 1. Process yt-dlp status
  const ytdlp = res.ytdlp || {};
  if (modalYtdlpInstalled && ytdlp.current) {
    modalYtdlpInstalled.textContent = `v${ytdlp.current}`;
  }
  if (modalYtdlpLatest && ytdlp.latest) {
    modalYtdlpLatest.textContent = `v${ytdlp.latest}`;
  }

  if (ytdlp.error) {
    if (ytdlpStatusBadge) {
      ytdlpStatusBadge.className = 'status-badge error';
      ytdlpStatusBadge.textContent = 'Check Failed';
    }
    if (runYtdlpUpdateBtn) runYtdlpUpdateBtn.style.display = 'none';
    if (!silent) {
      showToast("yt-dlp check: " + ytdlp.error, "error");
    }
  } else if (ytdlp.update_available) {
    if (ytdlpStatusBadge) {
      ytdlpStatusBadge.className = 'status-badge available';
      ytdlpStatusBadge.textContent = `Update Available (v${ytdlp.latest})`;
    }
    if (runYtdlpUpdateBtn) runYtdlpUpdateBtn.style.display = 'inline-flex';
    if (restartAppBtn) restartAppBtn.style.display = 'none';
    if (updateNoticeDot) updateNoticeDot.style.display = 'block';
  } else {
    if (ytdlpStatusBadge) {
      ytdlpStatusBadge.className = 'status-badge uptodate';
      ytdlpStatusBadge.textContent = 'Up to date ✓';
    }
    if (runYtdlpUpdateBtn) runYtdlpUpdateBtn.style.display = 'none';
    if (restartAppBtn) restartAppBtn.style.display = 'none';
  }

  // 2. Process App release status
  const app = res.app || {};
  if (modalAppInstalled && app.current) {
    modalAppInstalled.textContent = `v${app.current}`;
  }
  if (modalAppLatest && app.latest) {
    modalAppLatest.textContent = `v${app.latest}`;
  }

  if (app.error) {
    if (appStatusBadge) {
      appStatusBadge.className = 'status-badge error';
      appStatusBadge.textContent = 'Check Failed';
    }
    if (runAppUpdateBtn) runAppUpdateBtn.style.display = 'none';
    if (appNotesBox) appNotesBox.style.display = 'none';
    if (!silent) {
      showToast("App check: " + app.error, "error");
    }
  } else if (app.update_available) {
    if (appStatusBadge) {
      appStatusBadge.className = 'status-badge available';
      appStatusBadge.textContent = `New Version Available (v${app.latest})`;
    }
    if (runAppUpdateBtn) {
      if (app.can_auto_update === false) {
        runAppUpdateBtn.innerHTML = '<span>🌐</span> Open Release Download Page';
      } else {
        runAppUpdateBtn.innerHTML = `<span>⚡</span> Download &amp; Run v${escapeHtml(app.latest)} Setup Wizard`;
      }
      runAppUpdateBtn.style.display = 'inline-flex';
    }
    if (app.notes && appNotesBox && appNotesContent) {
      appNotesContent.textContent = app.notes;
      appNotesBox.style.display = 'block';
    }
    if (updateNoticeDot) updateNoticeDot.style.display = 'block';
  } else {
    if (appStatusBadge) {
      appStatusBadge.className = 'status-badge uptodate';
      appStatusBadge.textContent = "You're up to date ✓";
    }
    if (runAppUpdateBtn) runAppUpdateBtn.style.display = 'none';
    if (appNotesBox) appNotesBox.style.display = 'none';
  }

  // Say on the Update button what the dot is for
  if (updateBtn) {
    const parts = [];
    if (ytdlp.update_available) parts.push(`Download engine update: v${ytdlp.latest}`);
    if (app.update_available) parts.push(`New app version: v${app.latest}`);
    if (parts.length) {
      updateBtn.title = parts.join('\n') + '\nClick to review and install.';
    } else if (ytdlp.error || app.error) {
      updateBtn.title = "Couldn't check for updates right now. Click to try again.";
    } else {
      updateBtn.title = "You're up to date";
    }
  }

  // Toast feedback if up to date or update available
  if (!ytdlp.update_available && !app.update_available && !ytdlp.error && !app.error) {
    if (openModal) {
      showToast("You're up to date! yt-dlp core and App are on the latest versions.", "success");
    }
    if (updateNoticeDot) updateNoticeDot.style.display = 'none';
  } else if (ytdlp.update_available || app.update_available) {
    showToast("Updates available! Click the Update button to review and install.", "info", 6000);
  }
}

window.onBackgroundUpdateCheck = function(res) {
  applyUpdateCheckResult(res, { openModal: false, silent: true });
};

async function checkUpdates(openModal = true, silent = false) {
  if (!window.pywebview || !window.pywebview.api) {
    if (!silent) showToast("Application engine is initializing...", "info");
    return;
  }

  if (!silent) {
    if (updateBtn) updateBtn.disabled = true;
    if (updateBtnIcon) updateBtnIcon.classList.add('spinning');
    if (updateBtnLabel) updateBtnLabel.textContent = 'Checking...';
  }
  if (recheckIcon) recheckIcon.classList.add('spinning');
  if (recheckUpdatesBtn) recheckUpdatesBtn.disabled = true;

  if (ytdlpStatusBadge) {
    ytdlpStatusBadge.className = 'status-badge checking';
    ytdlpStatusBadge.textContent = 'Checking PyPI...';
  }
  if (appStatusBadge) {
    appStatusBadge.className = 'status-badge checking';
    appStatusBadge.textContent = 'Checking GitHub...';
  }

  if (openModal) {
    openUpdateModal();
  }

  try {
    const res = await window.pywebview.api.check_updates();
    applyUpdateCheckResult(res, { openModal, silent });
  } catch (err) {
    if (openModal && !silent) {
      showToast("Update check failed: " + err, "error");
    }
    if (ytdlpStatusBadge) {
      ytdlpStatusBadge.className = 'status-badge error';
      ytdlpStatusBadge.textContent = 'Error';
    }
    if (appStatusBadge) {
      appStatusBadge.className = 'status-badge error';
      appStatusBadge.textContent = 'Error';
    }
  } finally {
    if (updateBtn) updateBtn.disabled = false;
    if (updateBtnIcon) updateBtnIcon.classList.remove('spinning');
    if (updateBtnLabel) updateBtnLabel.textContent = 'Update';
    if (recheckIcon) recheckIcon.classList.remove('spinning');
    if (recheckUpdatesBtn) recheckUpdatesBtn.disabled = false;
  }
}

// Bind Update & Recheck Buttons
if (updateBtn) {
  updateBtn.addEventListener('click', () => checkUpdates(true));
}
if (recheckUpdatesBtn) {
  recheckUpdatesBtn.addEventListener('click', () => checkUpdates(false));
}

// Global Progress Hooks invoked from Python
window.update_ytdlp_progress = function(percent, message) {
  if (ytdlpProgressFill) ytdlpProgressFill.style.width = `${percent}%`;
  if (ytdlpProgressMsg && message) ytdlpProgressMsg.textContent = message;
};

window.update_app_progress = function(percent, message) {
  if (appProgressFill) appProgressFill.style.width = `${percent}%`;
  if (appProgressMsg && message) appProgressMsg.textContent = message;
};

// yt-dlp Update Execution
if (runYtdlpUpdateBtn) {
  runYtdlpUpdateBtn.addEventListener('click', async () => {
    runYtdlpUpdateBtn.disabled = true;
    runYtdlpUpdateBtn.innerHTML = '<span>⏳</span> Updating...';
    if (ytdlpProgressBox) ytdlpProgressBox.style.display = 'flex';
    if (ytdlpProgressFill) ytdlpProgressFill.style.width = '10%';
    if (ytdlpProgressMsg) ytdlpProgressMsg.textContent = 'Connecting to PyPI...';

    try {
      const res = await window.pywebview.api.update_ytdlp();
      if (res && res.success) {
        if (ytdlpProgressFill) ytdlpProgressFill.style.width = '100%';
        if (ytdlpProgressMsg) ytdlpProgressMsg.textContent = `✓ Successfully updated to v${res.version}!`;
        runYtdlpUpdateBtn.style.display = 'none';
        if (restartAppBtn) restartAppBtn.style.display = 'inline-flex';
        if (ytdlpStatusBadge) {
          ytdlpStatusBadge.className = 'status-badge uptodate';
          ytdlpStatusBadge.textContent = `Updated to v${res.version}`;
        }
        showToast(`yt-dlp updated to v${res.version}. Please restart the app.`, "success", 6000);
      } else {
        const err = (res && res.error) ? res.error : "Unknown error";
        if (ytdlpProgressMsg) ytdlpProgressMsg.textContent = "Update failed: " + err;
        runYtdlpUpdateBtn.disabled = false;
        runYtdlpUpdateBtn.innerHTML = '<span>⚡</span> Retry Update';
        showToast("yt-dlp update failed: " + err, "error");
      }
    } catch (err) {
      if (ytdlpProgressMsg) ytdlpProgressMsg.textContent = "Update failed: " + err;
      runYtdlpUpdateBtn.disabled = false;
      runYtdlpUpdateBtn.innerHTML = '<span>⚡</span> Retry Update';
      showToast("Error updating yt-dlp: " + err, "error");
    }
  });
}

// Restart Application Handler
if (restartAppBtn) {
  restartAppBtn.addEventListener('click', async () => {
    restartAppBtn.disabled = true;
    restartAppBtn.innerHTML = '<span>⏳</span> Restarting App...';
    showToast("Restarting Husnexa...", "info", 3000);
    try {
      await window.pywebview.api.restart_app();
    } catch (err) {
      console.error("Restart error:", err);
    }
  });
}

// App Update Execution (Download Setup.exe and launch installer wizard)
if (runAppUpdateBtn) {
  runAppUpdateBtn.addEventListener('click', async () => {
    if (!lastCheckedUpdates || !lastCheckedUpdates.app) {
      showToast("Download details not found.", "error");
      return;
    }

    const appInfo = lastCheckedUpdates.app;
    if (appInfo.can_auto_update === false) {
      showToast("Opening release page in browser...", "info");
      await window.pywebview.api.open_url(appInfo.html_url || appInfo.asset_url);
      return;
    }

    const assetUrl = appInfo.asset_url;
    if (!assetUrl) {
      showToast("Download URL not found.", "error");
      return;
    }
    const assetName = appInfo.asset_name || "Husnexa_Setup.exe";
    const expectedSize = appInfo.size_bytes || 0;
    const expectedSha256 = appInfo.expected_sha256 || "";

    runAppUpdateBtn.disabled = true;
    runAppUpdateBtn.innerHTML = '<span>⏳</span> Downloading update...';
    if (appProgressBox) appProgressBox.style.display = 'flex';
    if (appProgressFill) appProgressFill.style.width = '5%';
    if (appProgressMsg) appProgressMsg.textContent = 'Connecting to download server...';

    try {
      const res = await window.pywebview.api.download_app_update(assetUrl, assetName, expectedSize, expectedSha256);
      if (res && res.success) {
        if (appProgressFill) appProgressFill.style.width = '100%';
        if (res.dev_mode) {
          if (appProgressMsg) appProgressMsg.textContent = `✓ Downloaded Setup package (Dev Mode): ${res.file_path}`;
          runAppUpdateBtn.style.display = 'none';
          showToast("Update downloaded to temp folder (Running from Python source).", "info", 7000);
        } else {
          if (appProgressMsg) appProgressMsg.textContent = '✓ Setup verified! Launching installer wizard...';
          runAppUpdateBtn.innerHTML = '<span>⏳</span> Launching Setup...';
          showToast("Update ready. Launching installer...", "success", 3000);
          setTimeout(async () => {
            try {
              await window.pywebview.api.apply_app_update(res.file_path);
            } catch (applyErr) {
              console.error("Apply update error:", applyErr);
              showToast("Failed to launch installer: " + applyErr, "error");
              runAppUpdateBtn.disabled = false;
              runAppUpdateBtn.innerHTML = '<span>📥</span> Retry Update';
            }
          }, 1500);
        }
      } else {
        const err = (res && res.error) ? res.error : "Unknown error";
        showToast("App update failed: " + err, "error");
        if (appProgressMsg) appProgressMsg.textContent = "Download failed: " + err;
        runAppUpdateBtn.disabled = false;
        runAppUpdateBtn.innerHTML = '<span>📥</span> Retry Update';
      }
    } catch (err) {
      if (appProgressMsg) appProgressMsg.textContent = "Download failed: " + err;
      runAppUpdateBtn.disabled = false;
      runAppUpdateBtn.innerHTML = '<span>📥</span> Retry Update';
      showToast("Error updating app: " + err, "error");
    }
  });
}

// ================= POST-DOWNLOAD ACTIONS =================
if (openFileBtn) {
  openFileBtn.addEventListener('click', async () => {
    if (lastDownloadedFilePath) {
      const res = await window.pywebview.api.play_file(lastDownloadedFilePath);
      if (res && res.error) showToast("Unable to play: " + res.error, "error");
    }
  });
}

if (showFolderBtn) {
  showFolderBtn.addEventListener('click', async () => {
    if (lastDownloadedFilePath) {
      await window.pywebview.api.show_in_folder(lastDownloadedFilePath);
    } else {
      const outDir = destPathText.textContent.trim();
      await window.pywebview.api.open_directory(outDir);
    }
  });
}

// Clears the finished download's Play / Show-in-folder bar and brings back the
// Start button, so a new link can be analyzed and downloaded right away.
function clearFinishedDownload() {
  lastDownloadedFilePath = null;
  if (postDownloadBar) postDownloadBar.style.display = 'none';
  startDownloadBtn.style.display = 'inline-flex';
  if (!isDownloading && !activeQueueJob) {
    resetProgress();
    progressCard.classList.remove('show');
  }
  updateDownloadButtonState();
}

if (newDownloadBtn) {
  newDownloadBtn.addEventListener('click', () => {
    clearFinishedDownload();
    singleUrlInput.value = '';
    singleUrlInput.focus();
    previewCard.classList.remove('show');
    currentSingleData = null;
    updateDownloadButtonState();
  });
}

// ================= SMART CLIPBOARD AUTO-DETECT =================
let _clipboardCheckBusy = false;
let _lastClipboardCheckTs = 0;

async function checkClipboardUrl() {
  if (!window.pywebview || !window.pywebview.api) return;
  const now = Date.now();
  if (_clipboardCheckBusy || (now - _lastClipboardCheckTs < 400)) return;
  _clipboardCheckBusy = true;
  _lastClipboardCheckTs = now;
  try {
    const res = await window.pywebview.api.check_clipboard_url();
    if (res && res.has_url) {
      const url = res.url.trim();
      const currentVal = singleUrlInput ? singleUrlInput.value.trim() : '';
      if (url && url !== lastDismissedClipboardUrl && url !== currentVal) {
        if (clipboardPill && clipboardUrlText) {
          clipboardUrlText.textContent = url;
          clipboardPill.style.display = 'flex';
        }
      }
    }
  } catch (e) {
  } finally {
    _clipboardCheckBusy = false;
  }
}

window.addEventListener('focus', checkClipboardUrl);

if (clipboardAnalyzeBtn) {
  clipboardAnalyzeBtn.addEventListener('click', () => {
    if (clipboardUrlText && singleUrlInput) {
      singleUrlInput.value = clipboardUrlText.textContent.trim();
      if (clipboardPill) clipboardPill.style.display = 'none';
      if (analyzeBtn) analyzeBtn.click();
    }
  });
}

if (clipboardDismissBtn) {
  clipboardDismissBtn.addEventListener('click', () => {
    if (clipboardUrlText) {
      lastDismissedClipboardUrl = clipboardUrlText.textContent.trim();
    }
    if (clipboardPill) clipboardPill.style.display = 'none';
  });
}

// ================= RECENT DOWNLOADS HISTORY =================
// Shows the last few downloads under the Start button, or the drop-a-link hint when empty
function renderRecentPanel(history) {
  const list = document.getElementById('recentList');
  const empty = document.getElementById('recentEmpty');
  const viewAll = document.getElementById('recentViewAllBtn');
  if (!list || !empty) return;
  const all = history || [];
  const items = all.slice(0, 4);
  list.innerHTML = '';
  empty.style.display = items.length ? 'none' : 'flex';
  if (viewAll) viewAll.style.display = all.length > items.length ? 'inline-flex' : 'none';
  items.forEach((item) => {
    const row = document.createElement('div');
    row.className = 'recent-item';
    const isAudio = /mp3|m4a|wav|audio/i.test(item.format || '');
    const thumb = /^https?:\/\//i.test(item.thumbnail || '')
      ? `<img class="recent-thumb" src="${escapeHtml(item.thumbnail)}" alt="">`
      : `<div class="recent-thumb">${isAudio ? '🎵' : '🎬'}</div>`;
    const missing = item.file_exists === false;
    row.innerHTML = `
      ${thumb}
      <div class="recent-info">
        <div class="recent-name" title="${escapeHtml(item.title || '')}">${escapeHtml(item.title || 'Download')}</div>
        <div class="recent-meta">${escapeHtml(item.format || 'Media')}${item.timestamp ? ' • ' + escapeHtml(item.timestamp) : ''}${missing ? ' • file moved or deleted' : ''}</div>
      </div>
      <div class="recent-actions">
        ${missing ? '' : `<button class="history-btn-mini" data-act="play" title="Play">▶ Play</button>
        <button class="history-btn-mini" data-act="folder" title="Show in folder">📁</button>`}
      </div>`;
    row.querySelectorAll('button').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (!item.file_path) return;
        if (btn.dataset.act === 'play') {
          const res = await window.pywebview.api.play_file(item.file_path);
          if (res && res.error) showToast("Unable to play: " + res.error, "error");
        } else {
          await window.pywebview.api.show_in_folder(item.file_path);
        }
      });
    });
    list.appendChild(row);
  });
}

const recentViewAllBtn = document.getElementById('recentViewAllBtn');
if (recentViewAllBtn) recentViewAllBtn.addEventListener('click', () => openHistoryModal());

async function updateHistoryCount() {
  if (!window.pywebview || !window.pywebview.api) return;
  try {
    const history = await window.pywebview.api.get_history();
    renderRecentPanel(history);
    if (historyBadge) {
      if (history && history.length > 0) {
        historyBadge.textContent = history.length;
        historyBadge.style.display = 'inline-block';
      } else {
        historyBadge.style.display = 'none';
      }
    }
  } catch (e) {}
}

async function openHistoryModal() {
  if (!window.pywebview || !window.pywebview.api) return;
  if (historyModalOverlay) historyModalOverlay.classList.add('show');
  await renderHistoryList();
}

function closeHistoryModal() {
  if (historyModalOverlay) historyModalOverlay.classList.remove('show');
}

async function renderHistoryList() {
  if (!historyList) return;
  historyList.innerHTML = '<div class="history-empty-state">Loading history...</div>';
  try {
    const history = await window.pywebview.api.get_history();
    if (historyCountSubtitle) {
      historyCountSubtitle.textContent = `${history.length} file${history.length === 1 ? '' : 's'} downloaded`;
    }
    if (!history || history.length === 0) {
      historyList.innerHTML = '<div class="history-empty-state">No recent downloads yet.</div>';
      return;
    }
    historyList.innerHTML = '';
    history.forEach(item => {
      const row = document.createElement('div');
      row.className = `history-item ${item.file_exists === false ? 'file-missing' : ''}`;
      
      const thumbHtml = /^https?:\/\//i.test(item.thumbnail || '')
        ? `<img class="history-thumb" src="${escapeHtml(item.thumbnail)}" alt="Thumbnail" />`
        : `<div class="history-thumb" style="display:flex;align-items:center;justify-content:center;color:#64748b;font-size:20px;">🎬</div>`;

      const missingBadge = item.file_exists === false 
        ? `<span class="history-chip missing" title="File not found on disk">Missing ⚠️</span>` 
        : '';

      row.innerHTML = `
        ${thumbHtml}
        <div class="history-meta">
          <div class="history-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</div>
          <div class="history-sub-row">
            <span class="history-chip">${escapeHtml(item.format || 'Media')}</span>
            ${missingBadge}
            ${item.size ? `<span>${escapeHtml(item.size)}</span> •` : ''}
            <span>${escapeHtml(item.duration || '')}</span> •
            <span>${escapeHtml(item.timestamp || '')}</span>
          </div>
        </div>
        <div class="history-actions">
          <button class="history-btn-mini primary" data-action="play" title="Play Media">▶ Play</button>
          <button class="history-btn-mini" data-action="folder" title="Show in Folder">📁 Folder</button>
          <button class="history-btn-mini delete" data-action="delete" title="Delete from history">✕</button>
        </div>
      `;

      row.querySelector('[data-action="play"]').addEventListener('click', async () => {
        if (item.file_path) {
          const res = await window.pywebview.api.play_file(item.file_path);
          if (res && res.error) showToast("File not found on disk", "error");
        }
      });

      row.querySelector('[data-action="folder"]').addEventListener('click', async () => {
        if (item.file_path) {
          await window.pywebview.api.show_in_folder(item.file_path);
        }
      });

      row.querySelector('[data-action="delete"]').addEventListener('click', async (e) => {
        e.stopPropagation();
        await window.pywebview.api.delete_history_item(item.id || item.file_path);
        await renderHistoryList();
        updateHistoryCount();
        showToast("History item removed", "info", 2000);
      });

      historyList.appendChild(row);
    });
  } catch (err) {
    historyList.innerHTML = `<div class="history-empty-state">Error: ${escapeHtml(err)}</div>`;
  }
}

if (historyBtn) historyBtn.addEventListener('click', openHistoryModal);
if (closeHistoryModalBtn) closeHistoryModalBtn.addEventListener('click', closeHistoryModal);
if (dismissHistoryBtn) dismissHistoryBtn.addEventListener('click', closeHistoryModal);
if (clearHistoryBtn) {
  clearHistoryBtn.addEventListener('click', async () => {
    await window.pywebview.api.clear_history();
    await renderHistoryList();
    updateHistoryCount();
    showToast("Download history cleared", "info", 2500);
  });
}

// Always open scrolled to the top so the header is never clipped on launch.
(function resetScrollToTop() {
  const toTop = () => { try { window.scrollTo(0, 0); document.documentElement.scrollTop = 0; document.body.scrollTop = 0; } catch (e) {} };
  toTop();
  window.addEventListener('load', () => { toTop(); setTimeout(toTop, 150); setTimeout(toTop, 600); });
})();
