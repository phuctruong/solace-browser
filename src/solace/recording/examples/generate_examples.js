/**
 * Solace Browser - Generate Example Episodes
 * Auth: 65537 | Phase 2: Episode Recording
 *
 * Generates 5 example episodes demonstrating various interaction types.
 * Run: node generate_examples.js
 */

const fs = require("fs");
const path = require("path");
const { EpisodeRecorder } = require("../recorder.js");

const EXAMPLES_DIR = __dirname;

function makeSnapshot(url, bodyChildren) {
  return {
    v: 1,
    meta: { url, viewport: { w: 1920, h: 1080 } },
    dom: {
      tag: "html",
      text: "",
      attrs: {},
      children: [
        {
          tag: "body",
          text: "",
          attrs: {},
          children: bodyChildren,
        },
      ],
    },
  };
}

// --- Example 1: Gmail Compose ---

function generateGmailCompose() {
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://mail.google.com/mail/u/0/", { w: 1920, h: 1080 });

  recorder.attachSnapshot(0, makeSnapshot("https://mail.google.com/mail/u/0/", [
    {
      tag: "nav",
      text: "",
      attrs: { role: "navigation", "aria-label": "Main" },
      children: [
        { tag: "button", text: "Compose", attrs: { "aria-label": "Compose", role: "button" }, children: [] },
      ],
    },
  ]));

  recorder.recordClick({ selector: "div[data-tooltip='Compose']", reference: "Compose" });

  recorder.recordType(
    { selector: "input[aria-label='To']", reference: "To" },
    "phuc@example.com"
  );

  recorder.recordType(
    { selector: "input[aria-label='Subject']", reference: "Subject" },
    "Meeting Tomorrow"
  );

  recorder.recordType(
    { selector: "div[aria-label='Message Body']", reference: "Message Body" },
    "Hi Phuc, can we meet at 3pm? Thanks!"
  );

  recorder.recordClick({ selector: "div[aria-label='Send']", reference: "Send" });

  recorder.stopRecording();
  return recorder;
}

// --- Example 2: Reddit Post ---

function generateRedditPost() {
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://www.reddit.com/r/programming/", { w: 1920, h: 1080 });

  recorder.attachSnapshot(0, makeSnapshot("https://www.reddit.com/r/programming/", [
    {
      tag: "nav",
      text: "",
      attrs: { role: "navigation", "aria-label": "Subreddit navigation" },
      children: [],
    },
    {
      tag: "button",
      text: "Create Post",
      attrs: { "aria-label": "Create Post", role: "button" },
      children: [],
    },
  ]));

  recorder.recordClick({ selector: "button[aria-label='Create Post']", reference: "Create Post" });

  recorder.recordType(
    { selector: "textarea[placeholder='Title']", reference: "Title" },
    "Show HN: Solace Browser - Chromium fork with native recording"
  );

  recorder.recordType(
    { selector: "div[data-testid='post-body']", reference: "Post Body" },
    "We built a custom Chromium fork that records browser interactions natively, without any extension."
  );

  recorder.recordClick({ selector: "button[type='submit']", reference: "Post" });

  recorder.stopRecording();
  return recorder;
}

// --- Example 3: GitHub Search ---

function generateGithubSearch() {
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://github.com", { w: 1920, h: 1080 });

  recorder.attachSnapshot(0, makeSnapshot("https://github.com", [
    {
      tag: "form",
      text: "",
      attrs: { role: "form", "aria-label": "Search" },
      children: [
        { tag: "input", text: "", attrs: { name: "q", placeholder: "Search GitHub", type: "text" }, children: [] },
      ],
    },
  ]));

  recorder.recordType(
    { selector: "input[name='q']", reference: "Search GitHub" },
    "solace browser automation"
  );

  recorder.recordSubmit({ selector: "form[aria-label='Search']", reference: "Search" });

  recorder.recordNavigate("https://github.com/search?q=solace+browser+automation");

  recorder.recordClick({
    selector: "a[href='/example/solace-browser']",
    reference: "solace-browser repository",
  });

  recorder.stopRecording();
  return recorder;
}

// --- Example 4: Form with Select ---

function generateFormWithSelect() {
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://example.com/signup", { w: 1920, h: 1080 });

  recorder.attachSnapshot(0, makeSnapshot("https://example.com/signup", [
    {
      tag: "form",
      text: "",
      attrs: { role: "form", "aria-label": "Sign Up" },
      children: [
        { tag: "input", text: "", attrs: { name: "email", placeholder: "Email", type: "email" }, children: [] },
        { tag: "input", text: "", attrs: { name: "password", placeholder: "Password", type: "password" }, children: [] },
        { tag: "input", text: "", attrs: { name: "name", placeholder: "Full Name", type: "text" }, children: [] },
      ],
    },
  ]));

  recorder.recordType(
    { selector: "input[name='email']", reference: "Email" },
    "user@example.com"
  );

  recorder.recordType(
    { selector: "input[name='password']", reference: "Password" },
    "securepassword123"
  );

  recorder.recordType(
    { selector: "input[name='name']", reference: "Full Name" },
    "Jane Doe"
  );

  recorder.recordSelect(
    { selector: "select#country", reference: "Country" },
    "US"
  );

  recorder.recordSelect(
    { selector: "select#timezone", reference: "Timezone" },
    "America/Los_Angeles"
  );

  recorder.recordSubmit({ selector: "form[aria-label='Sign Up']", reference: "Sign Up" });

  recorder.stopRecording();
  return recorder;
}

// --- Example 5: Multi-page Navigation ---

function generateMultiPageNav() {
  const recorder = new EpisodeRecorder();
  recorder.startRecording("https://news.ycombinator.com", { w: 1920, h: 1080 });

  recorder.attachSnapshot(0, makeSnapshot("https://news.ycombinator.com", [
    {
      tag: "nav",
      text: "",
      attrs: { role: "navigation" },
      children: [
        { tag: "a", text: "new", attrs: { href: "/newest" }, children: [] },
        { tag: "a", text: "comments", attrs: { href: "/newcomments" }, children: [] },
        { tag: "a", text: "ask", attrs: { href: "/ask" }, children: [] },
      ],
    },
  ]));

  recorder.recordClick({ selector: "a[href='/newest']", reference: "new" });
  recorder.recordNavigate("https://news.ycombinator.com/newest");

  recorder.recordClick({
    selector: "a.titleline",
    reference: "First article link",
  });
  recorder.recordNavigate("https://example.com/article/1");

  recorder.recordNavigate("https://news.ycombinator.com");

  recorder.recordClick({ selector: "a[href='/ask']", reference: "ask" });
  recorder.recordNavigate("https://news.ycombinator.com/ask");

  recorder.stopRecording();
  return recorder;
}

// --- Generate All ---

const examples = [
  { name: "gmail-compose", generator: generateGmailCompose, desc: "Gmail email composition" },
  { name: "reddit-post", generator: generateRedditPost, desc: "Reddit post creation" },
  { name: "github-search", generator: generateGithubSearch, desc: "GitHub search and navigation" },
  { name: "signup-form", generator: generateFormWithSelect, desc: "Signup form with select elements" },
  { name: "multi-page-nav", generator: generateMultiPageNav, desc: "Multi-page navigation on HN" },
];

console.log("Generating example episodes...\n");

for (const { name, generator, desc } of examples) {
  const recorder = generator();
  const json = recorder.serializeEpisode();
  const episode = recorder.getEpisode();

  const filepath = path.join(EXAMPLES_DIR, `${name}.json`);
  fs.writeFileSync(filepath, json, { mode: 0o600 });

  // Validate
  const errors = recorder.validateEpisode();

  console.log(`  ${name}.json`);
  console.log(`    Description: ${desc}`);
  console.log(`    Domain: ${episode.domain}`);
  console.log(`    Actions: ${episode.action_count}`);
  console.log(`    Snapshots: ${Object.keys(episode.snapshots).length}`);
  console.log(`    Validation: ${errors.length === 0 ? "PASS" : "FAIL: " + errors.join(", ")}`);
  console.log(`    Size: ${json.length} bytes`);
  console.log();
}

// Generate JSONL index
const indexLines = examples.map(({ generator }) => {
  const recorder = generator();
  recorder.stopRecording();
  return recorder.getIndexEntry();
});

fs.writeFileSync(
  path.join(EXAMPLES_DIR, "episodes.jsonl"),
  indexLines.join("\n") + "\n",
  { mode: 0o600 }
);

console.log(`Generated ${examples.length} example episodes + index`);
console.log(`Location: ${EXAMPLES_DIR}`);
