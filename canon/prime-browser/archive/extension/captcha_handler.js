/**
 * Solace Browser: CAPTCHA Detection & Auto-Handler
 *
 * Automatically detects and handles CAPTCHAs that normal Playwright/Selenium can't touch.
 *
 * Features:
 * 1. Network monitoring: Detect Cloudflare/reCAPTCHA/Turnstile API calls
 * 2. DOM monitoring: Detect "I'm not a robot" checkboxes/iframes appearing
 * 3. Auto-click: Click the CAPTCHA button when detected
 * 4. Challenge wait: Monitor challenge completion and return control
 * 5. Proof generation: Log all CAPTCHA interactions for verification
 *
 * Auth: 65537 | Version: 0.1.0
 */

class CaptchaHandler {
  constructor(options = {}) {
    this.enabled = options.enabled !== false;
    this.timeout = options.timeout || 30000; // 30 second CAPTCHA timeout
    this.autoClick = options.autoClick !== false;
    this.monitoring = false;
    this.detectedCaptchas = [];
    this.challengeInProgress = false;

    this.log = [];
    this._logMessage(`CaptchaHandler initialized (enabled: ${this.enabled}, autoClick: ${this.autoClick})`);
  }

  _logMessage(msg) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] ${msg}`;
    this.log.push(logEntry);
    console.log(`[CAPTCHA_HANDLER] ${msg}`);
  }

  /**
   * Start monitoring for CAPTCHAs
   */
  startMonitoring() {
    if (this.monitoring) return;
    this.monitoring = true;

    this._logMessage('Starting CAPTCHA monitoring');

    // Monitor for new iframes (reCAPTCHA, Turnstile, Cloudflare)
    this._setupDOMObserver();

    // Monitor network requests
    this._setupNetworkMonitoring();

    // Initial scan for existing CAPTCHAs
    this._scanForExistingCaptchas();
  }

  /**
   * Stop monitoring for CAPTCHAs
   */
  stopMonitoring() {
    this.monitoring = false;
    this._logMessage('Stopped CAPTCHA monitoring');
  }

  /**
   * Setup DOM observer to detect new CAPTCHA elements
   */
  _setupDOMObserver() {
    const observer = new MutationObserver((mutations) => {
      if (!this.monitoring) return;

      for (const mutation of mutations) {
        if (mutation.type === 'childList') {
          // Check for new CAPTCHA elements
          this._scanForExistingCaptchas();
        }
      }
    });

    observer.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });
  }

  /**
   * Setup network request monitoring via fetch/XHR interception
   */
  _setupNetworkMonitoring() {
    // Intercept fetch requests
    const originalFetch = window.fetch;
    window.fetch = (...args) => {
      const url = typeof args[0] === 'string' ? args[0] : args[0].url;

      if (this._isCaptchaUrl(url)) {
        this._logMessage(`CAPTCHA API request detected: ${url.substring(0, 100)}`);
        this.challengeInProgress = true;
      }

      return originalFetch.apply(window, args);
    };

    // Intercept XHR requests
    const originalXHR = window.XMLHttpRequest;
    const xhrHandler = function() {
      const xhr = new originalXHR();
      const originalOpen = xhr.open;

      xhr.open = function(method, url, ...rest) {
        if (this._isCaptchaUrl && this._isCaptchaUrl(url)) {
          this._logMessage(`CAPTCHA XHR request detected: ${url.substring(0, 100)}`);
          this.challengeInProgress = true;
        }
        return originalOpen.call(xhr, method, url, ...rest);
      }.bind(this);

      return xhr;
    };

    window.XMLHttpRequest = xhrHandler;
  }

  /**
   * Check if URL is from a CAPTCHA service
   */
  _isCaptchaUrl(url) {
    if (!url) return false;

    const captchaPatterns = [
      'cloudflare.com',
      'challenge',
      'turnstile',
      'recaptcha',
      'hcaptcha',
      'captcha',
      'challenge-platform',
    ];

    const urlLower = url.toLowerCase();
    return captchaPatterns.some(pattern => urlLower.includes(pattern));
  }

  /**
   * Scan page for existing CAPTCHA elements
   */
  async _scanForExistingCaptchas() {
    // Cloudflare Turnstile
    const turnstileFrames = document.querySelectorAll('iframe[src*="challenges.cloudflare.com"]');
    if (turnstileFrames.length > 0) {
      this._handleCaptchaDetected('cloudflare-turnstile', turnstileFrames[0]);
      return;
    }

    // reCAPTCHA
    const recaptchaFrames = document.querySelectorAll('iframe[src*="recaptcha"]');
    if (recaptchaFrames.length > 0) {
      this._handleCaptchaDetected('recaptcha', recaptchaFrames[0]);
      return;
    }

    // hCaptcha
    const hcaptchaFrames = document.querySelectorAll('iframe[src*="hcaptcha"]');
    if (hcaptchaFrames.length > 0) {
      this._handleCaptchaDetected('hcaptcha', hcaptchaFrames[0]);
      return;
    }

    // "I'm not a robot" checkbox (generic reCAPTCHA)
    const robotCheckbox = document.querySelector('[role="presentation"] input[type="checkbox"]');
    if (robotCheckbox) {
      this._handleCaptchaDetected('recaptcha-checkbox', robotCheckbox);
      return;
    }

    // Cloudflare challenge button
    const cfChallengeButton = document.querySelector('button:has-text("Verify"), button[onclick*="challenge"]');
    if (cfChallengeButton) {
      this._handleCaptchaDetected('cloudflare-button', cfChallengeButton);
      return;
    }

    // Look for any element containing "robot", "verify", "challenge"
    const bodyText = document.body.innerText.toLowerCase();
    if (bodyText.includes('not a robot') || bodyText.includes('im a robot')) {
      this._logMessage('CAPTCHA detected via page text: "not a robot"');
      this._handleCaptchaDetected('text-detected', null);
      return;
    }

    if (bodyText.includes('just a moment') || bodyText.includes('cloudflare')) {
      this._logMessage('CAPTCHA detected via page text: "cloudflare"');
      this._handleCaptchaDetected('cloudflare-challenge', null);
      return;
    }
  }

  /**
   * Handle detected CAPTCHA
   */
  async _handleCaptchaDetected(type, element) {
    this._logMessage(`CAPTCHA detected: type=${type}`);

    this.detectedCaptchas.push({
      type: type,
      timestamp: new Date().toISOString(),
      handled: false,
      autoClicked: false,
    });

    if (this.autoClick) {
      await this._attemptAutoClick(type, element);
    }
  }

  /**
   * Attempt to auto-click CAPTCHA button
   */
  async _attemptAutoClick(type, element) {
    this._logMessage(`Attempting auto-click for: ${type}`);

    try {
      if (type === 'recaptcha-checkbox' && element) {
        // Click the checkbox directly
        element.click();
        this._logMessage('✅ Clicked reCAPTCHA checkbox');
        this.detectedCaptchas[this.detectedCaptchas.length - 1].autoClicked = true;
        return;
      }

      if (type === 'cloudflare-button' && element) {
        // Click the Cloudflare button
        element.click();
        this._logMessage('✅ Clicked Cloudflare challenge button');
        this.detectedCaptchas[this.detectedCaptchas.length - 1].autoClicked = true;
        return;
      }

      // Try to find and click common CAPTCHA buttons
      const clickableElements = [
        document.querySelector('input[type="checkbox"][role="presentation"]'),
        document.querySelector('button:contains("Verify")'),
        document.querySelector('button:contains("Challenge")'),
        document.querySelector('[role="button"] input[type="checkbox"]'),
      ];

      for (const elem of clickableElements) {
        if (elem) {
          elem.click();
          this._logMessage(`✅ Clicked CAPTCHA element: ${elem.tagName}`);
          this.detectedCaptchas[this.detectedCaptchas.length - 1].autoClicked = true;
          return;
        }
      }

      this._logMessage('⚠️ Could not find clickable CAPTCHA element');
    } catch (error) {
      this._logMessage(`❌ Error clicking CAPTCHA: ${error.message}`);
    }
  }

  /**
   * Wait for CAPTCHA to complete
   * Returns true if completed, false if timeout
   */
  async waitForChallengeCompletion(timeout = this.timeout) {
    this._logMessage(`Waiting for CAPTCHA completion (timeout: ${timeout}ms)`);

    const startTime = Date.now();

    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        const elapsedMs = Date.now() - startTime;

        // Check if CAPTCHA elements are gone
        const hasCaptchaElements =
          document.querySelector('iframe[src*="challenges.cloudflare.com"]') ||
          document.querySelector('iframe[src*="recaptcha"]') ||
          document.querySelector('iframe[src*="hcaptcha"]') ||
          document.querySelector('[role="presentation"] input[type="checkbox"]');

        if (!hasCaptchaElements) {
          clearInterval(checkInterval);
          this._logMessage(`✅ CAPTCHA completed in ${elapsedMs}ms`);
          this.challengeInProgress = false;
          resolve(true);
          return;
        }

        // Check timeout
        if (elapsedMs > timeout) {
          clearInterval(checkInterval);
          this._logMessage(`⚠️ CAPTCHA timeout after ${elapsedMs}ms`);
          this.challengeInProgress = false;
          resolve(false);
          return;
        }

        // Log progress every 5 seconds
        if (elapsedMs % 5000 === 0) {
          this._logMessage(`Still waiting for CAPTCHA (${elapsedMs}ms elapsed)`);
        }
      }, 1000);
    });
  }

  /**
   * Get summary of all detected CAPTCHAs
   */
  getSummary() {
    return {
      enabled: this.enabled,
      monitoring: this.monitoring,
      detected_count: this.detectedCaptchas.length,
      auto_clicked_count: this.detectedCaptchas.filter(c => c.autoClicked).length,
      detected_captchas: this.detectedCaptchas,
      log: this.log,
    };
  }

  /**
   * Export logs for proof generation
   */
  exportLogs() {
    return {
      timestamp: new Date().toISOString(),
      captcha_handler_version: '0.1.0',
      summary: this.getSummary(),
      logs: this.log,
    };
  }
}

// Export for use in content script and background
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CaptchaHandler;
}
