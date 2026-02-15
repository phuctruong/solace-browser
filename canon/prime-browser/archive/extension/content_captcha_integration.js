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

  // Log to extension
  chrome.runtime.sendMessage({
    type: 'CAPTCHA_HANDLER_INITIALIZED',
    url: window.location.href,
    summary: captchaHandler.getSummary(),
  });
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
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeCaptchaHandler);
} else {
  initializeCaptchaHandler();
}

// Log initialization
console.log('[SOLACE_CAPTCHA] Content script loaded for:', window.location.href);
