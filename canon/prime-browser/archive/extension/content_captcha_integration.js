/**
 * Solace Browser: Content Script Integration for CAPTCHA Handling
 *
 * Automatically initializes CAPTCHA handler for protected sites.
 *
 * Usage:
 * - Add this to manifest.json content_scripts
 * - Automatically detects and handles CAPTCHAs
 * - No additional code needed
 *
 * Auth: 65537
 */

// List of sites that commonly use Cloudflare CAPTCHA
const CLOUDFLARE_PROTECTED_SITES = [
  'medium.com',
  'producthunt.com',
  'stripe.com',
  'discord.com',
  'cloudflare.com',
  // Add more as needed
];

// Initialize CAPTCHA handler immediately
let captchaHandler = null;

/**
 * Initialize CAPTCHA handling for the page
 */
function initializeCaptchaHandler() {
  try {
    // Debug: Check if CaptchaHandler class is available
    if (typeof CaptchaHandler === 'undefined') {
      console.error('[SOLACE_CAPTCHA] ERROR: CaptchaHandler class not found! Script loading issue?');
      console.log('[SOLACE_CAPTCHA] Available on window:', Object.keys(window).filter(k => k.includes('Captcha') || k.includes('CAPTCHA')));
      return;
    }

    console.log('[SOLACE_CAPTCHA] CaptchaHandler class found, initializing...');

    // Create handler instance
    captchaHandler = new CaptchaHandler({
      enabled: true,
      autoClick: true,
      timeout: 30000,
    });

    // Start monitoring
    captchaHandler.startMonitoring();

    console.log('[SOLACE_CAPTCHA] CAPTCHA handler initialized and monitoring started');

    // Expose API to window for Playwright access
    window.solace_captcha = {
      handler: captchaHandler,
      getSummary: () => captchaHandler.getSummary(),
      getLogs: () => captchaHandler.log,
      waitForCompletion: (timeout) => captchaHandler.waitForChallengeCompletion(timeout),
      isMonitoring: () => captchaHandler.monitoring,
      exportProof: () => captchaHandler.exportLogs(),
    };

    console.log('[SOLACE_CAPTCHA] window.solace_captcha API exposed');

    // Log to extension (wrap in try-catch in case extension context isn't ready)
    try {
      chrome.runtime.sendMessage({
        type: 'CAPTCHA_HANDLER_INITIALIZED',
        url: window.location.href,
        summary: captchaHandler.getSummary(),
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.log('[SOLACE_CAPTCHA] Note: Extension not responding to init message (may be expected)');
        } else {
          console.log('[SOLACE_CAPTCHA] Extension acknowledged initialization');
        }
      });
    } catch (e) {
      console.log('[SOLACE_CAPTCHA] Could not send message to extension (expected in some contexts):', e.message);
    }
  } catch (error) {
    console.error('[SOLACE_CAPTCHA] FATAL ERROR during initialization:', error);
    console.error('[SOLACE_CAPTCHA] Stack:', error.stack);
  }
}

/**
 * Check if this site is Cloudflare-protected
 */
function isCloudflareProtectedSite() {
  const hostname = window.location.hostname;
  return CLOUDFLARE_PROTECTED_SITES.some(site => hostname.includes(site));
}

/**
 * Listen for messages from Playwright/automation
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_CAPTCHA_STATUS') {
    sendResponse({
      status: 'ok',
      monitoring: captchaHandler ? captchaHandler.monitoring : false,
      detected: captchaHandler ? captchaHandler.detectedCaptchas.length : 0,
      summary: captchaHandler ? captchaHandler.getSummary() : null,
    });
  }

  if (request.type === 'WAIT_FOR_CAPTCHA') {
    if (captchaHandler) {
      captchaHandler.waitForChallengeCompletion(request.timeout || 30000).then((completed) => {
        sendResponse({
          completed: completed,
          logs: captchaHandler.exportLogs(),
        });
      });
    } else {
      sendResponse({
        completed: false,
        error: 'CAPTCHA handler not initialized',
      });
    }
    return true; // Will respond asynchronously
  }
});

// Initialize when DOM is ready
console.log('[SOLACE_CAPTCHA] Content script loaded for:', window.location.href);
console.log('[SOLACE_CAPTCHA] Document readyState:', document.readyState);
console.log('[SOLACE_CAPTCHA] Is CaptchaHandler defined?', typeof CaptchaHandler !== 'undefined');

if (document.readyState === 'loading') {
  console.log('[SOLACE_CAPTCHA] Document still loading, waiting for DOMContentLoaded...');
  document.addEventListener('DOMContentLoaded', () => {
    console.log('[SOLACE_CAPTCHA] DOMContentLoaded fired');
    initializeCaptchaHandler();
  });
} else {
  console.log('[SOLACE_CAPTCHA] Document already loaded, initializing immediately...');
  initializeCaptchaHandler();
}
