/**
 * Solace Browser Campaign Orchestrator - Phase 7
 *
 * Marketing automation integration for multi-platform campaign execution.
 * Orchestrates posting workflows across Reddit, HackerNews, Twitter/LinkedIn,
 * and Email via the Solace Browser extension WebSocket protocol.
 *
 * Architecture:
 *   - CampaignOrchestrator: main controller with dry-run + execute modes
 *   - PlatformWorkflow: per-platform step executor
 *   - ProofCollector: generates cryptographic proof of campaign actions
 *   - ErrorRecovery: retry + rollback for failed steps
 *
 * Auth: 65537 | Northstar: Phuc Forecast
 * Verification: 641 -> 274177 -> 65537
 */

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

// ===== Constants =====

const CAMPAIGN_VERSION = "1.0.0";
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;
const STEP_TIMEOUT_MS = 30000;

const PLATFORM_CONFIGS = {
  reddit: {
    name: "Reddit",
    baseUrl: "https://www.reddit.com",
    submitPath: "/submit",
    rateLimit: { postsPerHour: 1, commentsPerHour: 10 },
  },
  hackernews: {
    name: "HackerNews",
    baseUrl: "https://news.ycombinator.com",
    submitPath: "/submit",
    rateLimit: { postsPerHour: 1, commentsPerHour: 5 },
  },
  twitter: {
    name: "Twitter",
    baseUrl: "https://twitter.com",
    composePath: "/compose/tweet",
    rateLimit: { postsPerHour: 5 },
  },
  linkedin: {
    name: "LinkedIn",
    baseUrl: "https://www.linkedin.com",
    composePath: "/feed/",
    rateLimit: { postsPerHour: 3 },
  },
  email: {
    name: "Email (Gmail)",
    baseUrl: "https://mail.google.com",
    composePath: "/mail/u/0/#inbox?compose=new",
    rateLimit: { emailsPerHour: 20 },
  },
};

const VALID_STATES = [
  "IDLE",
  "LOADING",
  "DRY_RUN",
  "APPROVED",
  "EXECUTING",
  "VERIFYING",
  "COMPLETED",
  "FAILED",
  "ROLLED_BACK",
];

const VALID_TRANSITIONS = {
  IDLE: ["LOADING"],
  LOADING: ["DRY_RUN", "FAILED"],
  DRY_RUN: ["APPROVED", "FAILED"],
  APPROVED: ["EXECUTING", "IDLE"],
  EXECUTING: ["VERIFYING", "FAILED"],
  VERIFYING: ["COMPLETED", "FAILED"],
  COMPLETED: ["IDLE"],
  FAILED: ["ROLLED_BACK", "IDLE"],
  ROLLED_BACK: ["IDLE"],
};

const STEP_TYPES = [
  "navigate",
  "click",
  "type",
  "wait",
  "snapshot",
  "verify",
  "extract",
];

// ===== Campaign State =====

class CampaignState {
  constructor(campaignId) {
    this.campaignId = campaignId;
    this.state = "IDLE";
    this.steps = [];
    this.completedSteps = [];
    this.failedSteps = [];
    this.proofs = [];
    this.startTime = null;
    this.endTime = null;
    this.auditLog = [];
  }

  transition(newState, reason = "") {
    const allowed = VALID_TRANSITIONS[this.state] || [];
    if (!allowed.includes(newState)) {
      throw new Error(
        `Invalid campaign transition: ${this.state} -> ${newState} (${reason})`
      );
    }
    const oldState = this.state;
    this.state = newState;
    this.auditLog.push({
      from: oldState,
      to: newState,
      reason,
      timestamp: new Date().toISOString(),
    });
    return this;
  }

  toJSON() {
    return {
      campaignId: this.campaignId,
      state: this.state,
      totalSteps: this.steps.length,
      completedSteps: this.completedSteps.length,
      failedSteps: this.failedSteps.length,
      proofCount: this.proofs.length,
      startTime: this.startTime,
      endTime: this.endTime,
      auditLog: this.auditLog,
    };
  }
}

// ===== Proof Collector =====

class ProofCollector {
  constructor() {
    this.proofs = [];
  }

  addProof(stepIndex, action, result) {
    const proofData = JSON.stringify(
      { stepIndex, action, result, timestamp: new Date().toISOString() },
      null,
      0
    );
    const hash = crypto.createHash("sha256").update(proofData).digest("hex");
    const proof = {
      stepIndex,
      action: action.type,
      hash,
      timestamp: new Date().toISOString(),
      success: result.success !== false,
    };
    this.proofs.push(proof);
    return proof;
  }

  generateChainHash() {
    const hashes = this.proofs.map((p) => p.hash);
    const chainInput = hashes.join("");
    return crypto.createHash("sha256").update(chainInput).digest("hex");
  }

  generateCertificate(campaignId) {
    return {
      version: CAMPAIGN_VERSION,
      campaignId,
      proofCount: this.proofs.length,
      chainHash: this.generateChainHash(),
      proofs: this.proofs,
      generatedAt: new Date().toISOString(),
    };
  }

  reset() {
    this.proofs = [];
  }
}

// ===== Error Recovery =====

class ErrorRecovery {
  constructor(maxRetries = MAX_RETRIES, retryDelay = RETRY_DELAY_MS) {
    this.maxRetries = maxRetries;
    this.retryDelay = retryDelay;
    this.retryCount = new Map();
  }

  canRetry(stepIndex) {
    const count = this.retryCount.get(stepIndex) || 0;
    return count < this.maxRetries;
  }

  recordRetry(stepIndex) {
    const count = this.retryCount.get(stepIndex) || 0;
    this.retryCount.set(stepIndex, count + 1);
    return count + 1;
  }

  getRetryCount(stepIndex) {
    return this.retryCount.get(stepIndex) || 0;
  }

  async waitBeforeRetry(stepIndex) {
    const count = this.getRetryCount(stepIndex);
    const delay = this.retryDelay * Math.pow(2, count);
    await new Promise((resolve) => setTimeout(resolve, delay));
  }

  reset() {
    this.retryCount.clear();
  }
}

// ===== Platform Workflows =====

class PlatformWorkflow {
  constructor(platform, config) {
    if (!PLATFORM_CONFIGS[platform]) {
      throw new Error(`Unknown platform: ${platform}`);
    }
    this.platform = platform;
    this.platformConfig = PLATFORM_CONFIGS[platform];
    this.config = config || {};
  }

  generateSteps() {
    switch (this.platform) {
      case "reddit":
        return this._redditSteps();
      case "hackernews":
        return this._hackernewsSteps();
      case "twitter":
        return this._twitterSteps();
      case "linkedin":
        return this._linkedinSteps();
      case "email":
        return this._emailSteps();
      default:
        throw new Error(`No workflow for platform: ${this.platform}`);
    }
  }

  _redditSteps() {
    const subreddit = this.config.subreddit || "test";
    const title = this.config.title || "";
    const body = this.config.body || "";
    return [
      {
        type: "navigate",
        url: `${this.platformConfig.baseUrl}/r/${subreddit}/submit`,
        description: `Navigate to r/${subreddit} submit page`,
      },
      {
        type: "wait",
        duration: 2000,
        description: "Wait for page load",
      },
      {
        type: "snapshot",
        step: "before_fill",
        description: "Capture pre-fill state",
      },
      {
        type: "click",
        selector: '[data-testid="post-title-input"], textarea[name="title"], #title-field',
        description: "Focus title field",
      },
      {
        type: "type",
        selector: '[data-testid="post-title-input"], textarea[name="title"], #title-field',
        text: title,
        description: "Enter post title",
      },
      {
        type: "click",
        selector: '[data-testid="post-body-input"], .DraftEditor-root, [role="textbox"]',
        description: "Focus body field",
      },
      {
        type: "type",
        selector: '[data-testid="post-body-input"], .DraftEditor-root, [role="textbox"]',
        text: body,
        description: "Enter post body",
      },
      {
        type: "snapshot",
        step: "before_submit",
        description: "Capture pre-submit state",
      },
      {
        type: "click",
        selector: 'button[type="submit"], [data-testid="submit-button"]',
        description: "Click submit button",
      },
      {
        type: "wait",
        duration: 3000,
        description: "Wait for submission",
      },
      {
        type: "snapshot",
        step: "after_submit",
        description: "Capture post-submit state",
      },
      {
        type: "verify",
        check: "url_changed",
        description: "Verify post was created (URL changed)",
      },
      {
        type: "extract",
        fields: ["url", "title"],
        description: "Extract post URL for proof",
      },
    ];
  }

  _hackernewsSteps() {
    const title = this.config.title || "";
    const url = this.config.url || "";
    const text = this.config.text || "";
    return [
      {
        type: "navigate",
        url: `${this.platformConfig.baseUrl}/submit`,
        description: "Navigate to HN submit page",
      },
      {
        type: "wait",
        duration: 1500,
        description: "Wait for page load",
      },
      {
        type: "snapshot",
        step: "before_fill",
        description: "Capture pre-fill state",
      },
      {
        type: "type",
        selector: 'input[name="title"]',
        text: title,
        description: "Enter story title",
      },
      {
        type: "type",
        selector: 'input[name="url"]',
        text: url,
        description: "Enter story URL",
      },
      ...(text
        ? [
            {
              type: "type",
              selector: 'textarea[name="text"]',
              text: text,
              description: "Enter story text",
            },
          ]
        : []),
      {
        type: "snapshot",
        step: "before_submit",
        description: "Capture pre-submit state",
      },
      {
        type: "click",
        selector: 'input[type="submit"]',
        description: "Click submit",
      },
      {
        type: "wait",
        duration: 2000,
        description: "Wait for submission",
      },
      {
        type: "snapshot",
        step: "after_submit",
        description: "Capture post-submit state",
      },
      {
        type: "verify",
        check: "url_changed",
        description: "Verify story was submitted",
      },
    ];
  }

  _twitterSteps() {
    const text = this.config.text || "";
    return [
      {
        type: "navigate",
        url: `${this.platformConfig.baseUrl}/compose/tweet`,
        description: "Navigate to Twitter compose",
      },
      {
        type: "wait",
        duration: 2000,
        description: "Wait for compose modal",
      },
      {
        type: "snapshot",
        step: "before_compose",
        description: "Capture compose state",
      },
      {
        type: "click",
        selector: '[data-testid="tweetTextarea_0"], [role="textbox"]',
        description: "Focus tweet textbox",
      },
      {
        type: "type",
        selector: '[data-testid="tweetTextarea_0"], [role="textbox"]',
        text: text,
        description: "Type tweet content",
      },
      {
        type: "snapshot",
        step: "before_post",
        description: "Capture pre-post state",
      },
      {
        type: "click",
        selector: '[data-testid="tweetButton"], [data-testid="tweetButtonInline"]',
        description: "Click tweet/post button",
      },
      {
        type: "wait",
        duration: 3000,
        description: "Wait for post",
      },
      {
        type: "snapshot",
        step: "after_post",
        description: "Capture post-tweet state",
      },
      {
        type: "verify",
        check: "toast_success",
        description: "Verify tweet was posted",
      },
    ];
  }

  _linkedinSteps() {
    const text = this.config.text || "";
    return [
      {
        type: "navigate",
        url: this.platformConfig.baseUrl + this.platformConfig.composePath,
        description: "Navigate to LinkedIn feed",
      },
      {
        type: "wait",
        duration: 2000,
        description: "Wait for feed load",
      },
      {
        type: "click",
        selector: ".share-box-feed-entry__trigger, .artdeco-button--muted",
        description: "Click Start a post",
      },
      {
        type: "wait",
        duration: 1500,
        description: "Wait for compose modal",
      },
      {
        type: "snapshot",
        step: "before_compose",
        description: "Capture compose state",
      },
      {
        type: "type",
        selector: '.ql-editor, [role="textbox"], .editor-content',
        text: text,
        description: "Type post content",
      },
      {
        type: "snapshot",
        step: "before_post",
        description: "Capture pre-post state",
      },
      {
        type: "click",
        selector: ".share-actions__primary-action, button.artdeco-button--primary",
        description: "Click Post button",
      },
      {
        type: "wait",
        duration: 3000,
        description: "Wait for post",
      },
      {
        type: "snapshot",
        step: "after_post",
        description: "Capture post state",
      },
      {
        type: "verify",
        check: "modal_closed",
        description: "Verify post was published",
      },
    ];
  }

  _emailSteps() {
    const to = this.config.to || "";
    const subject = this.config.subject || "";
    const body = this.config.body || "";
    return [
      {
        type: "navigate",
        url: this.platformConfig.baseUrl + this.platformConfig.composePath,
        description: "Navigate to Gmail compose",
      },
      {
        type: "wait",
        duration: 2000,
        description: "Wait for compose window",
      },
      {
        type: "snapshot",
        step: "before_compose",
        description: "Capture compose state",
      },
      {
        type: "type",
        selector: 'input[name="to"], [aria-label="To"]',
        text: to,
        description: "Enter recipient",
      },
      {
        type: "type",
        selector: 'input[name="subjectbox"], [aria-label="Subject"]',
        text: subject,
        description: "Enter subject",
      },
      {
        type: "click",
        selector: '[role="textbox"][aria-label="Message Body"], .Am',
        description: "Focus message body",
      },
      {
        type: "type",
        selector: '[role="textbox"][aria-label="Message Body"], .Am',
        text: body,
        description: "Enter message body",
      },
      {
        type: "snapshot",
        step: "before_send",
        description: "Capture pre-send state",
      },
      {
        type: "click",
        selector: '[data-tooltip="Send"], [aria-label="Send"]',
        description: "Click send button",
      },
      {
        type: "wait",
        duration: 2000,
        description: "Wait for send confirmation",
      },
      {
        type: "snapshot",
        step: "after_send",
        description: "Capture post-send state",
      },
      {
        type: "verify",
        check: "sent_confirmation",
        description: "Verify email was sent",
      },
    ];
  }
}

// ===== Campaign Orchestrator =====

class CampaignOrchestrator {
  constructor(options = {}) {
    this.wsUrl = options.wsUrl || "ws://localhost:9222";
    this.outputDir = options.outputDir || path.join(process.cwd(), "output");
    this.dryRun = options.dryRun !== undefined ? options.dryRun : true;
    this.humanApproval = options.humanApproval !== undefined ? options.humanApproval : true;
    this.state = null;
    this.proofCollector = new ProofCollector();
    this.errorRecovery = new ErrorRecovery(
      options.maxRetries || MAX_RETRIES,
      options.retryDelay || RETRY_DELAY_MS
    );
    this.ws = null;
    this.pendingResponses = new Map();
    this.requestCounter = 0;
  }

  async loadCampaign(campaignFile) {
    let campaign;
    if (typeof campaignFile === "string") {
      const raw = fs.readFileSync(campaignFile, "utf-8");
      campaign = JSON.parse(raw);
    } else {
      campaign = campaignFile;
    }

    this._validateCampaign(campaign);

    const campaignId =
      campaign.id || `campaign_${Date.now()}_${crypto.randomBytes(4).toString("hex")}`;
    this.state = new CampaignState(campaignId);
    this.state.transition("LOADING", "campaign loaded");

    // Generate steps from platform workflows
    const allSteps = [];
    for (const target of campaign.targets || []) {
      const workflow = new PlatformWorkflow(target.platform, target);
      const steps = workflow.generateSteps();
      for (const step of steps) {
        step.platform = target.platform;
        step.targetIndex = campaign.targets.indexOf(target);
      }
      allSteps.push(...steps);
    }

    this.state.steps = allSteps;
    return {
      campaignId,
      platform: (campaign.targets || []).map((t) => t.platform),
      totalSteps: allSteps.length,
      steps: allSteps.map((s, i) => ({
        index: i,
        type: s.type,
        platform: s.platform,
        description: s.description,
      })),
    };
  }

  _validateCampaign(campaign) {
    if (!campaign || typeof campaign !== "object") {
      throw new Error("Campaign must be a non-null object");
    }
    if (!campaign.name || typeof campaign.name !== "string") {
      throw new Error("Campaign must have a name (string)");
    }
    if (!Array.isArray(campaign.targets) || campaign.targets.length === 0) {
      throw new Error("Campaign must have at least one target");
    }
    for (const target of campaign.targets) {
      if (!target.platform) {
        throw new Error("Each target must specify a platform");
      }
      if (!PLATFORM_CONFIGS[target.platform]) {
        throw new Error(`Unknown platform: ${target.platform}`);
      }
    }
  }

  async dryRunCampaign() {
    if (!this.state) {
      throw new Error("No campaign loaded. Call loadCampaign() first.");
    }

    this.state.transition("DRY_RUN", "starting dry run");

    const results = [];
    for (let i = 0; i < this.state.steps.length; i++) {
      const step = this.state.steps[i];
      results.push({
        index: i,
        type: step.type,
        platform: step.platform,
        description: step.description,
        wouldExecute: true,
        details: this._describeDryRunStep(step),
      });
    }

    return {
      campaignId: this.state.campaignId,
      mode: "dry_run",
      totalSteps: results.length,
      steps: results,
      readyForApproval: true,
      rateChecks: this._checkRateLimits(),
    };
  }

  _describeDryRunStep(step) {
    switch (step.type) {
      case "navigate":
        return { action: "Would navigate to", url: step.url };
      case "click":
        return { action: "Would click", selector: step.selector };
      case "type":
        return {
          action: "Would type",
          selector: step.selector,
          textLength: (step.text || "").length,
          textPreview: (step.text || "").substring(0, 50),
        };
      case "wait":
        return { action: "Would wait", duration: step.duration };
      case "snapshot":
        return { action: "Would take snapshot", step: step.step };
      case "verify":
        return { action: "Would verify", check: step.check };
      case "extract":
        return { action: "Would extract", fields: step.fields };
      default:
        return { action: `Unknown: ${step.type}` };
    }
  }

  _checkRateLimits() {
    const platformCounts = {};
    for (const step of this.state.steps) {
      if (step.type === "click" && step.description.toLowerCase().includes("submit")) {
        platformCounts[step.platform] = (platformCounts[step.platform] || 0) + 1;
      }
    }

    const checks = [];
    for (const [platform, count] of Object.entries(platformCounts)) {
      const config = PLATFORM_CONFIGS[platform];
      const limit = config.rateLimit.postsPerHour || config.rateLimit.emailsPerHour || 1;
      checks.push({
        platform,
        postCount: count,
        limit,
        ok: count <= limit,
      });
    }
    return checks;
  }

  async approveCampaign() {
    if (!this.state) {
      throw new Error("No campaign loaded");
    }
    this.state.transition("APPROVED", "campaign approved for execution");
    return { campaignId: this.state.campaignId, state: "APPROVED" };
  }

  async executeCampaign(sendCommand) {
    if (!this.state) {
      throw new Error("No campaign loaded");
    }
    if (this.state.state !== "APPROVED") {
      throw new Error(
        `Campaign must be APPROVED before execution (current: ${this.state.state})`
      );
    }

    this.state.transition("EXECUTING", "starting execution");
    this.state.startTime = new Date().toISOString();
    this.proofCollector.reset();
    this.errorRecovery.reset();

    const results = [];
    for (let i = 0; i < this.state.steps.length; i++) {
      const step = this.state.steps[i];
      let result;

      try {
        result = await this._executeStepWithRetry(step, i, sendCommand);
        this.state.completedSteps.push({ index: i, result });
        this.proofCollector.addProof(i, step, result);
        results.push({ index: i, success: true, result });
      } catch (error) {
        const failRecord = {
          index: i,
          error: error.message,
          retries: this.errorRecovery.getRetryCount(i),
        };
        this.state.failedSteps.push(failRecord);
        results.push({ index: i, success: false, error: error.message });

        // Non-critical steps (wait, snapshot) can be skipped
        if (step.type === "wait" || step.type === "snapshot") {
          continue;
        }
        // Critical failures stop the campaign
        this.state.transition("FAILED", `Step ${i} failed: ${error.message}`);
        break;
      }
    }

    if (this.state.state === "EXECUTING") {
      this.state.transition("VERIFYING", "all steps completed");
    }

    return {
      campaignId: this.state.campaignId,
      state: this.state.state,
      results,
      completedCount: this.state.completedSteps.length,
      failedCount: this.state.failedSteps.length,
    };
  }

  async _executeStepWithRetry(step, index, sendCommand) {
    while (true) {
      try {
        return await this._executeStep(step, index, sendCommand);
      } catch (error) {
        if (!this.errorRecovery.canRetry(index)) {
          throw error;
        }
        this.errorRecovery.recordRetry(index);
        await this.errorRecovery.waitBeforeRetry(index);
      }
    }
  }

  async _executeStep(step, index, sendCommand) {
    switch (step.type) {
      case "navigate":
        return await sendCommand({
          type: "NAVIGATE",
          payload: { url: step.url },
          request_id: `campaign_${this.state.campaignId}_step_${index}`,
        });

      case "click":
        return await sendCommand({
          type: "CLICK",
          payload: { selector: step.selector },
          request_id: `campaign_${this.state.campaignId}_step_${index}`,
        });

      case "type":
        return await sendCommand({
          type: "TYPE",
          payload: { selector: step.selector, text: step.text },
          request_id: `campaign_${this.state.campaignId}_step_${index}`,
        });

      case "wait":
        await new Promise((resolve) =>
          setTimeout(resolve, step.duration || 1000)
        );
        return { success: true, waited: step.duration };

      case "snapshot":
        return await sendCommand({
          type: "SNAPSHOT",
          payload: { step: step.step },
          request_id: `campaign_${this.state.campaignId}_step_${index}`,
        });

      case "verify":
        return await sendCommand({
          type: "EXTRACT_PAGE",
          payload: { check: step.check },
          request_id: `campaign_${this.state.campaignId}_step_${index}`,
        });

      case "extract":
        return await sendCommand({
          type: "EXTRACT_PAGE",
          payload: { fields: step.fields },
          request_id: `campaign_${this.state.campaignId}_step_${index}`,
        });

      default:
        throw new Error(`Unknown step type: ${step.type}`);
    }
  }

  async verifyCampaign() {
    if (!this.state || this.state.state !== "VERIFYING") {
      throw new Error("Campaign must be in VERIFYING state");
    }

    const certificate = this.proofCollector.generateCertificate(
      this.state.campaignId
    );

    const verification = {
      campaignId: this.state.campaignId,
      totalSteps: this.state.steps.length,
      completedSteps: this.state.completedSteps.length,
      failedSteps: this.state.failedSteps.length,
      proofCertificate: certificate,
      auditLog: this.state.auditLog,
      verified: this.state.failedSteps.length === 0,
    };

    this.state.endTime = new Date().toISOString();
    this.state.transition("COMPLETED", "verification complete");

    return verification;
  }

  async rollback() {
    if (!this.state || this.state.state !== "FAILED") {
      throw new Error("Can only rollback a FAILED campaign");
    }

    const rollbackInfo = {
      campaignId: this.state.campaignId,
      completedBeforeFailure: this.state.completedSteps.length,
      failedAt: this.state.failedSteps,
      message:
        "Browser actions are not reversible. Review failed steps and re-run.",
    };

    this.state.transition("ROLLED_BACK", "manual rollback");
    return rollbackInfo;
  }

  getState() {
    if (!this.state) return null;
    return this.state.toJSON();
  }

  getProofs() {
    return this.proofCollector.proofs;
  }

  reset() {
    this.state = null;
    this.proofCollector.reset();
    this.errorRecovery.reset();
  }

  async saveCampaignReport(outputPath) {
    if (!this.state) {
      throw new Error("No campaign to save");
    }

    const report = {
      version: CAMPAIGN_VERSION,
      campaign: this.state.toJSON(),
      proofs: this.proofCollector.generateCertificate(this.state.campaignId),
      steps: this.state.steps.map((s, i) => ({
        index: i,
        type: s.type,
        platform: s.platform,
        description: s.description,
      })),
      completedSteps: this.state.completedSteps,
      failedSteps: this.state.failedSteps,
      generatedAt: new Date().toISOString(),
    };

    const targetPath = outputPath || path.join(this.outputDir, `campaign_${this.state.campaignId}.json`);
    const dir = path.dirname(targetPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(targetPath, JSON.stringify(report, null, 2));
    return targetPath;
  }
}

// ===== Campaign Episode Builder =====

function buildCampaignEpisode(campaign) {
  if (!campaign || !campaign.targets) {
    throw new Error("Invalid campaign: missing targets");
  }

  const actions = [];
  for (const target of campaign.targets) {
    const workflow = new PlatformWorkflow(target.platform, target);
    const steps = workflow.generateSteps();
    for (const step of steps) {
      actions.push({
        type: step.type,
        platform: target.platform,
        data: step,
        timestamp: new Date().toISOString(),
      });
    }
  }

  return {
    session_id: `campaign_${Date.now()}`,
    domain: "multi-platform",
    actions,
    action_count: actions.length,
    metadata: {
      type: "campaign",
      name: campaign.name,
      platforms: campaign.targets.map((t) => t.platform),
      version: CAMPAIGN_VERSION,
    },
  };
}

// ===== Exports =====

module.exports = {
  CampaignOrchestrator,
  CampaignState,
  PlatformWorkflow,
  ProofCollector,
  ErrorRecovery,
  buildCampaignEpisode,
  CAMPAIGN_VERSION,
  PLATFORM_CONFIGS,
  VALID_STATES,
  VALID_TRANSITIONS,
  STEP_TYPES,
  MAX_RETRIES,
  RETRY_DELAY_MS,
  STEP_TIMEOUT_MS,
};
