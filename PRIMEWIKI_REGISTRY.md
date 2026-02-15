# PRIMEWIKI REGISTRY - Central Index of All Knowledge Nodes

**Auth**: 65537 | **Updated**: 2026-02-15 | **Status**: Production
**Purpose**: Know what website patterns have been discovered and mapped

---

## Quick Navigation

- **Gmail Knowledge Nodes** (2 nodes)
- **LinkedIn Knowledge Nodes** (2 nodes)
- **Reddit Knowledge Nodes** (3 nodes)
- **Total Landmarks Discovered** (800+)

---

## GMAIL KNOWLEDGE NODES

### ✅ gmail-oauth-flow.primewiki.md
- **Website**: mail.google.com
- **Tier**: 23 | **C-Score**: 0.95 | **G-Score**: 0.92
- **Type**: Authentication flow
- **Status**: Complete, Phase 1 verified
- **Landmarks**: 127+ (form fields, buttons, security screens)
- **Magic Words**:
  - "Verify it's you"
  - "Enter your password"
  - "2-Step Verification"
  - "Use an app password"
  - "Sign in"
- **Key Patterns**:
  - Email input field with validation
  - Password input field with validation
  - Multiple 2FA options (authenticator app, backup codes, security keys)
  - OAuth approval screen
- **Selectors Found**:
  - Email: `input[type="email"][aria-label="Email or phone"]`
  - Password: `input[type="password"]`
  - Next button: `button[aria-label="Next"]` or role-based
  - Sign in: `button[aria-label="Sign in"]`
- **Event Chains Required**:
  - Email: focus → input → change → keyup → blur
  - Password: focus → input → change → keyup → blur
- **Security Patterns**:
  - Rate limiting on failed attempts
  - Headless detection (use headed mode first)
  - Event validation (JavaScript, not just value)
  - Session persistence (save cookies)
- **Related Recipes**:
  - gmail-oauth-login.recipe.json
  - gmail-login-headed.recipe.json
- **Confidence**: 95% (tested multiple times)

### ✅ gmail-send-email.primewiki.md
- **Website**: mail.google.com (compose interface)
- **Tier**: 23 | **C-Score**: 0.95 | **G-Score**: 0.88
- **Type**: Email composition and sending
- **Status**: Complete
- **Landmarks**: 89+ (compose modal, form fields, buttons)
- **Magic Words**:
  - "Compose"
  - "To"
  - "Subject"
  - "Message body"
  - "Send"
  - "Draft saved"
  - "Message sent"
- **Key Patterns**:
  - Compose button in top navigation
  - Modal overlay for composition
  - Recipient field with autocomplete
  - Subject field
  - Body field (contenteditable div)
  - Attachment support
  - Save draft (auto)
  - Send button (disables during submission)
- **Selectors Found**:
  - Compose button: `button[aria-label="Compose"]`
  - To field: `input[aria-label="To"]`
  - Subject: `input[placeholder="Subject"]`
  - Body: `div[role="textbox"][aria-label="Message body"]`
  - Send: `button[aria-label="Send"]`
- **Related Recipes**:
  - gmail-send-email.recipe.json (depends on gmail-oauth-login)
- **Dependencies**:
  - Must be authenticated (gmail-oauth-flow)
  - Recipient must be valid email
  - Body can be empty (optional)
- **Confidence**: 95%

---

## LINKEDIN KNOWLEDGE NODES

### ✅ linkedin-profile-optimization.primewiki.md
- **Website**: linkedin.com/in/{username}
- **Tier**: 23 | **C-Score**: 0.99 | **G-Score**: 0.98
- **Type**: Profile information and optimization
- **Status**: Complete, expert analysis (10/10 score achieved)
- **Landmarks**: 412+ (form fields, buttons, sections)
- **Magic Words**:
  - "Edit intro"
  - "Add headline"
  - "Add about"
  - "Headline"
  - "About"
  - "Experience"
  - "Education"
  - "Skills"
  - "Recommendations"
  - "Save"
- **Key Patterns**:
  - Profile header with photo, headline, location
  - About section (markdown support)
  - Experience section (company, title, duration)
  - Education section
  - Skills section with endorsements
  - Recommendations section
  - All sections inline-editable (no page reload needed)
- **Selectors Pattern**: ARIA-based (CSS classes are dynamic)
  - Edit buttons: `role=button[name='Edit headline']`
  - Form fields: `role=textbox[aria-label='..']`
  - Save buttons: `role=button[name='Save']`
- **Critical Learning**: React dynamic UI requires role selectors, not class names
- **Optimization Rules**:
  - Headline: Include mobile hook + authority + keywords (max 220 chars)
  - About: Narrative format, personality + expertise (1000+ chars optimal)
  - Skills: 20+ skills with 3+ endorsements each
  - Recommendations: 5+ external recommendations
  - Profile completeness: 10/10 = all sections filled
- **Related Recipes**:
  - linkedin-profile-optimization-10-10.recipe.json
- **Confidence**: 99% (expert verified)

### ✅ linkedin-project-management.primewiki.md
- **Website**: linkedin.com/in/{username}/details/experience/projects
- **Tier**: 23 | **C-Score**: 0.95 | **G-Score**: 0.85
- **Type**: Project portfolio management
- **Status**: Complete
- **Landmarks**: 156+ (project cards, form fields, buttons)
- **Magic Words**:
  - "Add project"
  - "Edit project"
  - "Delete project"
  - "Project title"
  - "Description"
  - "Project URL"
  - "Members"
  - "Save"
- **Key Patterns**:
  - Project list view (grid or list)
  - Project card with title, description, collaborators
  - Add project modal
  - Edit project modal (same as add)
  - Delete confirmation
  - Contenteditable fields for description (not standard input)
- **Selectors Pattern**: Role-based
  - Add button: `role=button[name='Add project']`
  - Edit link: `role=link[name='Edit project {PROJECT_NAME}']`
  - Delete: context menu option or dedicated button
  - Title field: `role=textbox[aria-label='Project title']`
  - Description: `role=textbox[aria-label='Description']`
- **Contenteditable Handling**: Use "slowly" pattern with 15ms delay
- **Performance Optimization**: 2.73x speedup vs baseline
- **Related Recipes**:
  - linkedin-update-5-projects-hr-approved.recipe.json
  - add-linkedin-project-optimized.recipe.json
  - delete-linkedin-projects-openclaw.recipe.json
- **Confidence**: 97% (optimized with metrics)

---

## REDDIT KNOWLEDGE NODES

### ✅ reddit-homepage-phase1.primewiki.md
- **Website**: reddit.com (logged out)
- **Tier**: 23 | **C-Score**: 0.92 | **G-Score**: 0.88
- **Type**: Homepage layout and navigation (complete site map)
- **Status**: ✅ Phase 1 COMPLETE with PrimeMermaid diagrams
- **Exploration Method**: Live CLI + Browser Server API (OpenClaw-style)
- **Discovered**: 2026-02-15T06:26:00Z
- **Landmarks**: 24 major interactive elements
  - Header: 6 elements (logo, search, create, login, signup, menu)
  - Feed: 8 elements (post cards, voting, comments, share)
  - Sidebar: 5 elements (communities, join buttons)
  - Authentication-gated: 5 elements (voting, posting, saving)
- **PrimeMermaid Diagrams**:
  - Site Map: Complete page structure with all sections
  - Component Diagram: Button/form relationships and auth flows
  - Navigation Flows: How to move between pages
- **Magic Words**: 25+ (Home, Popular, Trending, Create post, Join, Subscribe, Comments, etc)
- **Selectors Validated**:
  - Post title: `a[data-testid="post-title"]` (0.90 confidence)
  - Upvote: `button[aria-label*="upvote"]` (0.93 confidence)
  - Community link: `a[href^="/r/"]` (0.95 confidence)
  - Login: `button:has-text("Log in")` (0.98 confidence)
  - Create post: `button:has-text("Create post")` (0.92 confidence)
- **Portal Architecture**:
  - homepage → login-page → authenticated-view
  - homepage → subreddit-page (click community)
  - homepage → post-detail (click post title)
  - post-card → comments (click comments link)
  - unauth-action → login-modal (voting, posting, saving gated)
- **Security Patterns Documented**:
  - Rate limiting: 5+ sec between actions
  - Authentication gates: voting, posting, commenting require login
  - Event chains: focus→input→change→blur for form fields
  - Session persistence: Save cookies after login for Phase 2
- **Phase 2 Ready**: ✅ All selectors validated, >85% confidence
- **Confidence**: 92% (Live exploration + PrimeMermaid validation)

### 🟡 reddit-authentication-flow.primewiki.json
- **Website**: reddit.com/login & reddit.com/register
- **Tier**: 23 | **C-Score**: 0.90 | **G-Score**: 0.88
- **Type**: User authentication
- **Status**: Phase 1 complete
- **Landmarks**: 67+ (form fields, buttons, OAuth options)
- **Magic Words**:
  - "Log in"
  - "Sign up"
  - "Email"
  - "Password"
  - "Username"
  - "Sign in with Google"
  - "Sign in with Apple"
  - "Sign in with Microsoft"
  - "2-factor authentication"
  - "Continue"
  - "Create account"
- **Authentication Methods**:
  - Email + password (standard)
  - Google OAuth
  - Apple OAuth
  - Microsoft OAuth
  - 2FA options (email, SMS, authenticator app)
- **Form Fields**:
  - Email input (login)
  - Password input (login)
  - Username input (signup)
  - Password input (signup)
  - Email input (signup)
  - Terms acceptance checkbox
  - reCAPTCHA (sometimes present)
- **Selectors Identified**:
  - Email field: `input[type="email"]`
  - Password field: `input[type="password"]`
  - Username field: `input[name="username"]` or similar
  - Login button: `button[type="submit"]` or `button:has-text("Log in")`
  - Signup link: `a[href="/register"]` or `button:has-text("Sign up")`
  - OAuth buttons: `button[aria-label*="Google"]`, etc
- **Security Patterns**:
  - Rate limiting on login attempts
  - CAPTCHA on repeated failures
  - Email verification required
  - 2FA optional
- **Related Recipes**:
  - reddit-login.recipe.json (Phase 1 complete, Phase 2 pending)
- **Phase 2 Pending**: OAuth flow testing, 2FA handling, session persistence
- **Confidence**: 90% (identified patterns, not yet Phase 2 tested)

### 🟡 reddit-subreddit-structure.primewiki.json
- **Website**: reddit.com/r/{subreddit_name}
- **Tier**: 23 | **C-Score**: 0.92 | **G-Score**: 0.80
- **Type**: Subreddit page layout
- **Status**: Phase 1 complete
- **Landmarks**: 156+ (post cards, buttons, sidebar)
- **Magic Words**:
  - "Create post"
  - "Post"
  - "Share"
  - "Subscribe"
  - "Subscribed"
  - "Joined"
  - "Members"
  - "Online"
  - "Sort by"
  - "Comments"
  - "Share"
  - "Award"
  - "Save"
- **Key Sections**:
  - Subreddit header (icon, name, description, subscribe button)
  - Sidebar with rules and community info
  - Main feed with post cards (same structure as homepage)
  - Post creation button/modal
  - Sort options (top, new, hot, best, controversial)
  - Filter options (today, week, month, year, all time)
- **Create Post Flow**:
  - Click "Create post" button
  - Modal opens with options:
    - Post type: text, link, image, video, poll
    - Title field
    - Content field (markdown supported)
    - Flair selection (optional)
    - NSFW toggle (if applicable)
    - Spoiler toggle
  - Submit button
- **Selectors Identified**:
  - Create post button: `button[aria-label*="Create post"]` or `button:has-text("Create post")`
  - Post title input: `input[placeholder*="Title"]`
  - Post body: `div[role="textbox"]` or contenteditable
  - Submit: `button:has-text("Post")` or role-based
  - Subscribe button: `button[aria-label*="Subscribe"]`
- **Portal Architecture**:
  - subreddit-page → create-post-modal → post-submitted → post-visible
  - subreddit-page → post-card → post-detail-page
  - subreddit-page → sidebar-info
- **Related Recipes**:
  - reddit-create-post.recipe.json (Phase 1 complete, Phase 2 pending)
- **Phase 2 Pending**: Post submission flow, moderation rules, community features
- **Confidence**: 92% (explored while logged out, create-post not tested)

---

## STATISTICS

| Metric | Count | Status |
|--------|-------|--------|
| Total Knowledge Nodes | 8 | ✅ Active |
| Tier 23 Nodes | 8 | ✅ Intermediate level |
| Nodes Phase 1 Complete | 8 | ✅ Fully mapped |
| Nodes Phase 2 Tested | 5 | ✅ Gmail (2) + LinkedIn (2) + Demo (1) |
| Nodes Phase 2 Pending | 3 | 🟡 Reddit (all 3) |
| **Total Landmarks** | **800+** | ✅ Discovered |
| **Average C-Score** | **0.94** | ✅ High coherence |
| **Average G-Score** | **0.90** | ✅ High gravity |

---

## HOW TO USE THIS REGISTRY

### I want to understand Gmail authentication
```bash
cat primewiki/gmail-oauth-flow.primewiki.md | jq '.selectors'
# Shows all stable selectors for email, password, submit buttons
# Includes event chain requirements and security patterns
```

### I want to know what Reddit patterns are known
```bash
grep -i reddit PRIMEWIKI_REGISTRY.md
# Returns: 3 nodes
# reddit-homepage-structure: 209 landmarks
# reddit-authentication-flow: 67 landmarks
# reddit-subreddit-structure: 156 landmarks
```

### I want to map a new website
```bash
# Check PRIMEWIKI_REGISTRY.md for that site
# If found: Load existing node, skip Phase 1
# If not found: Begin Phase 1 live exploration
#   1. Start browser server
#   2. Navigate using curl + live LLM reasoning
#   3. Extract landmarks, selectors, magic words
#   4. Create PrimeWiki node
#   5. Add to PRIMEWIKI_REGISTRY.md
```

### I want to understand LinkedIn's dynamic UI
```bash
cat primewiki/linkedin-profile-optimization.primewiki.md | grep -A 10 "Selectors"
# Shows: Use ARIA-based selectors (role=button, role=textbox)
# Explains: CSS classes are dynamic, accessibility tree is stable
# This pattern applies to all LinkedIn pages
```

---

## QUALITY METRICS

### Coherence Score (C-Score)
- **Formula**: (accurate_selectors / total_selectors) * (magic_words_found / expected)
- **Target**: 0.90+
- **Current**: 0.94 (excellent)
- **Meaning**: How well we understand the page structure

### Gravity Score (G-Score)
- **Formula**: (recipes_created / landmarks_found) * (phase2_success_rate)
- **Target**: 0.85+
- **Current**: 0.90 (excellent)
- **Meaning**: How useful the knowledge is for automation

### Confidence Intervals
- **95%** = Selectors tested multiple times, recipes in Phase 2
- **90%** = Selectors identified but Phase 2 not yet tested
- **85%** = Patterns identified, validation pending

---

## UPDATING THIS REGISTRY

**After Phase 1 Exploration:**
1. Create PrimeWiki node in primewiki/{domain}.primewiki.md
2. Add entry to PRIMEWIKI_REGISTRY.md with:
   - Website, Tier, C-Score, G-Score
   - Landmarks count, Magic Words
   - Key Patterns, Selectors Found
   - Portal Architecture
   - Confidence score
3. Link to related recipes (if any)
4. Commit: "docs(registry): Add {domain} PrimeWiki node"

**After Phase 2 Testing:**
1. Update Status from "Phase 1 complete" to "Phase 2 tested"
2. Update C-Score and G-Score based on actual Phase 2 results
3. Add notes about any selector adjustments needed
4. Commit: "docs(registry): Phase 2 verified for {domain}"

---

**Auth**: 65537 | **Northstar**: Phuc Forecast | **Last Updated**: 2026-02-15
**Principle**: "Know before you explore. Explore before you script. Script only what's proven."
