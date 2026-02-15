# Solace Browser Quick Start

**Learn Solace Browser in 5 minutes.** Three hands-on tutorials covering the essentials.

---

## Tutorial 1: Start the Browser Server (1 minute)

The browser server stays running so you can connect/disconnect anytime (20x faster than opening a new browser each time).

### Steps

```bash
# 1. Navigate to project directory
cd /home/phuc/projects/solace-browser

# 2. Start the persistent browser server
python persistent_browser_server.py
```

### What Happens

```
INFO: Starting Solace Browser Server
INFO: Chromium browser starting...
INFO: Server listening on http://localhost:9222
INFO: Browser ready for commands
```

### Success Indicator

When you see "Browser ready for commands", the server is running. The browser window stays open until you stop the server (Ctrl+C).

---

## Tutorial 2: Make Your First API Call (2 minutes)

Navigate to a website and capture its state using the HTTP API.

### Step 1: Navigate

```bash
curl -X POST http://localhost:9222/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Step 2: Get Clean HTML

```bash
curl http://localhost:9222/html-clean | jq -r '.html'
```

You'll see the page's HTML. This is what Claude reads to understand the page.

### Step 3: Take a Screenshot

```bash
curl http://localhost:9222/screenshot | jq '.image' > page.png
```

### Step 4: Get ARIA Tree (Accessibility Tree)

```bash
curl http://localhost:9222/aria | jq '.tree'
```

This shows the page's semantic structure (buttons, forms, links with labels).

### Common Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/navigate` | POST | Go to URL: `{"url": "..."}` |
| `/html-clean` | GET | Get cleaned HTML for LLM understanding |
| `/aria` | GET | Get accessibility tree with labels |
| `/screenshot` | GET | Get page screenshot |
| `/click` | POST | Click element: `{"selector": "..."}` |
| `/fill` | POST | Fill form: `{"selector": "...", "text": "..."}` |
| `/submit` | POST | Submit form: `{"selector": "..."}` |

---

## Tutorial 3: Save and Load Session (2 minutes)

After logging in, save the session so you don't need to re-login next time.

### Part A: Login and Save

```bash
# 1. Navigate to login page
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://linkedin.com/login"}'

# 2. Get page to see what fields exist
curl http://localhost:9222/html-clean | jq -r '.html'

# 3. Fill email field
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "input[type=email]", "text": "your-email@example.com"}'

# 4. Fill password field
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "input[type=password]", "text": "your-password"}'

# 5. Click login button
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Sign in\")"}'

# 6. Wait for redirect (check HTML to see if you're logged in)
curl http://localhost:9222/html-clean | jq -r '.html'

# 7. Save the session (cookies)
curl -X POST http://localhost:9222/save-session
```

This saves cookies to `artifacts/session.json`.

### Part B: Load Session Next Time

```bash
# 1. Navigate to login page
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://linkedin.com/login"}'

# 2. Load cookies from saved session
curl -X POST http://localhost:9222/load-session \
  -d '{"session_file": "artifacts/session.json"}'

# 3. Navigate to your profile (you're already logged in!)
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://linkedin.com/in/yourprofile/"}'

# Done! No re-login needed.
```

---

## Next Steps

- **Understand how it works** → Read [CORE_CONCEPTS.md](./CORE_CONCEPTS.md)
- **Learn expert patterns** → Read [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)
- **Debug when stuck** → Read [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)
- **Full API reference** → Read [API_REFERENCE.md](./API_REFERENCE.md)

---

## Troubleshooting

### "Connection refused" on localhost:9222

The server isn't running. Start it first:
```bash
python persistent_browser_server.py
```

### "Selector not found"

The HTML changed. Get fresh HTML to find the correct selector:
```bash
curl http://localhost:9222/html-clean | jq -r '.html' | grep -i "email"
```

### "Login failed after fill"

Sometimes websites need a delay. Check the HTML after filling to see what happened:
```bash
curl http://localhost:9222/html-clean | jq -r '.html'
```

Is there an error message? Is the field actually filled?

---

## Key Principles

1. **HTML First**: Always get `/html-clean` to understand page state before acting
2. **Verify Everything**: After each action (click, fill), check `/html-clean` to confirm it worked
3. **Use CSS Selectors**: Look for patterns like `button[aria-label="..."]`, `input[type=email]`, `a:has-text("...")`
4. **Save Sessions**: Once logged in, save with `/save-session` to avoid re-login

---

**Next**: [Go to CORE_CONCEPTS.md](./CORE_CONCEPTS.md) to understand how Solace Browser works
