// Adds a hover download button to YouTube's video player.
(() => {
  const VIDEO_ID = /^[\w-]{11}$/;
  const OPTIONS = [
    { label: 'Best quality', mediaType: 'video', quality: 'best' },
    { label: '1080p', mediaType: 'video', quality: '1080' },
    { label: '720p', mediaType: 'video', quality: '720' },
    { label: 'MP3 audio', mediaType: 'audio', quality: 'MP3' }
  ];
  const STYLES = `
    :host { position: absolute; top: 12px; right: 12px; z-index: 70; opacity: 0; pointer-events: none;
      transition: opacity 0.15s; font: 500 13px Roboto, Arial, sans-serif; }
    :host(.visible), :host(.open) { opacity: 1; pointer-events: auto; }
    button { font: inherit; color: #fff; border: 0; cursor: pointer; }
    .main { display: flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 18px;
      background: rgba(15, 23, 42, 0.86); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4); }
    .main:hover, .main:focus-visible { background: rgba(8, 145, 178, 0.95); }
    .menu { display: none; position: absolute; top: 38px; right: 0; min-width: 140px; padding: 4px;
      border-radius: 10px; background: rgba(15, 23, 42, 0.96); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5); }
    :host(.open) .menu { display: block; }
    .menu button { display: block; width: 100%; padding: 8px 10px; border-radius: 7px; text-align: left;
      background: transparent; }
    .menu button:hover, .menu button:focus-visible { background: rgba(8, 145, 178, 0.75); }
  `;

  let host = null;
  let mainButton = null;
  let resetTimer = null;

  function currentVideoId() {
    const url = new URL(location.href);
    const shorts = url.pathname.match(/^\/shorts\/([\w-]{11})/);
    const id = shorts ? shorts[1] : url.searchParams.get('v');
    return VIDEO_ID.test(id || '') ? id : null;
  }

  function currentTitle() {
    return document.title.replace(/^\(\d+\)\s*/, '').replace(/\s*-\s*YouTube$/, '');
  }

  function showStatus(text, seconds) {
    clearTimeout(resetTimer);
    mainButton.textContent = text;
    mainButton.title = text;
    if (seconds) {
      resetTimer = setTimeout(() => {
        mainButton.textContent = '⬇ Download';
        mainButton.title = 'Download with Husnexa';
      }, seconds * 1000);
    }
  }

  function request(option) {
    host.classList.remove('open');
    const videoId = currentVideoId();
    if (!videoId) return;
    showStatus('Sending...');
    const message = {
      type: 'download', videoId, title: currentTitle(), mediaType: option.mediaType, quality: option.quality
    };
    chrome.runtime.sendMessage(message, (reply) => {
      if (chrome.runtime.lastError) {
        showStatus('Reload this page and try again', 6);
      } else if (reply && reply.error) {
        showStatus(reply.error, 8);
      } else {
        showStatus('Added to app ✓', 3);
      }
    });
  }

  function buildButton() {
    const element = document.createElement('div');
    element.id = 'fsmd-download';
    const shadow = element.attachShadow({ mode: 'open' });
    const style = document.createElement('style');
    style.textContent = STYLES;
    const main = document.createElement('button');
    main.className = 'main';
    main.type = 'button';
    main.textContent = '⬇ Download';
    main.title = 'Download with Husnexa';
    main.setAttribute('aria-haspopup', 'menu');
    const menu = document.createElement('div');
    menu.className = 'menu';
    menu.setAttribute('role', 'menu');
    OPTIONS.forEach((option) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.textContent = option.label;
      item.setAttribute('role', 'menuitem');
      item.addEventListener('click', () => request(option));
      menu.appendChild(item);
    });
    main.addEventListener('click', () => element.classList.toggle('open'));
    // Keep clicks and key presses from pausing the video behind the button.
    ['click', 'dblclick', 'mousedown', 'mouseup', 'keydown', 'keyup'].forEach((name) => {
      element.addEventListener(name, (event) => event.stopPropagation());
    });
    shadow.append(style, main, menu);
    mainButton = main;
    return element;
  }

  function activePlayer() {
    if (!location.pathname.startsWith('/shorts/')) return document.querySelector('#movie_player');
    return [...document.querySelectorAll('#shorts-player')].find((player) => player.clientWidth > 0);
  }

  function attach() {
    const player = activePlayer();
    if (!player || !currentVideoId()) {
      if (host) host.remove();
      return;
    }
    if (!host) host = buildButton();
    if (host.parentElement === player) return;
    player.appendChild(host);
    if (player.dataset.fsmdHover) return;
    player.dataset.fsmdHover = 'true';
    player.addEventListener('mouseenter', () => host.classList.add('visible'));
    player.addEventListener('mousemove', () => host.classList.add('visible'));
    player.addEventListener('mouseleave', () => host.classList.remove('visible', 'open'));
  }

  // YouTube swaps pages without reloading, and the player can arrive after the page does.
  document.addEventListener('yt-navigate-finish', attach);
  document.addEventListener('yt-page-data-updated', attach);
  new MutationObserver(() => {
    if (!host || !host.isConnected) attach();
  }).observe(document.documentElement, { childList: true, subtree: true });
  attach();
})();
