// Passes download requests from the YouTube page to the app's native helper.
const NATIVE_HOST = 'com.husnexa.host';
const COOKIE_DOMAIN = 'youtube.com';
const VIDEO_ID = /^[\w-]{11}$/;
const SETUP_HELP = 'Husnexa helper not found. Install the app, then reload this page.';

async function readCookies() {
  const cookies = await chrome.cookies.getAll({ domain: COOKIE_DOMAIN });
  return cookies.map(({ name, value, domain, path, secure, expirationDate }) => (
    { name, value, domain, path, secure, expirationDate }
  ));
}

// The port stays open while the job is pending, so the app can ask for cookies if it needs them.
function sendToApp(request, respond) {
  const port = chrome.runtime.connectNative(NATIVE_HOST);
  let answered = false;

  port.onMessage.addListener(async (message) => {
    if (message.type === 'need_cookies') {
      let cookies = [];
      try {
        cookies = await readCookies();
      } catch (error) {
        console.warn('Could not read cookies:', error);
      }
      port.postMessage({ type: 'cookies', cookies });
    } else if (message.type === 'finished') {
      port.disconnect();
    } else if (!answered) {
      answered = true;
      respond(message);
      if (!message.job_id) port.disconnect();
    }
  });
  port.onDisconnect.addListener(() => {
    if (answered) return;
    answered = true;
    console.warn('Native helper error:', chrome.runtime.lastError?.message);
    respond({ error: SETUP_HELP });
  });
  port.postMessage(request);
}

chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (sender.id !== chrome.runtime.id || message?.type !== 'download') return false;
  // The link is rebuilt here so a page can only ever request a YouTube video.
  if (!VIDEO_ID.test(message.videoId || '')) {
    respond({ error: 'This page has no video to download.' });
    return false;
  }
  sendToApp({
    action: 'download',
    url: `https://www.youtube.com/watch?v=${message.videoId}`,
    media_type: message.mediaType === 'audio' ? 'audio' : 'video',
    quality: String(message.quality || 'best'),
    title: String(message.title || '').slice(0, 300)
  }, respond);
  return true;
});
