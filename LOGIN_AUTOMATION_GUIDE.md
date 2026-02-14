# SOLACE BROWSER - LOGIN AUTOMATION GUIDE

## Overview

Solace Browser can now automate login to major websites:
- ✅ LinkedIn
- ✅ Gmail
- ✅ GitHub
- ✅ Twitter/X
- ✅ More coming soon

## Setup Instructions

### Step 1: Configure Credentials

Edit `credentials.properties` in the project root:

```bash
nano credentials.properties
```

Add your login credentials:

```properties
# LinkedIn
linkedin.email=your-email@example.com
linkedin.password=your-password-here

# Gmail
gmail.email=your-email@gmail.com
gmail.password=your-password-here

# GitHub
github.username=your-username
github.password=your-token-or-password

# Twitter
twitter.email=your-email@example.com
twitter.password=your-password-here
```

### Step 2: Keep Credentials Private

⚠️ **WARNING**: Never commit `credentials.properties` to git!

```bash
# Add to .gitignore
echo "credentials.properties" >> .gitignore
```

### Step 3: Run Login Automation

```bash
# Automated login to all configured sites
python3 solace_login_automation.py

# This will:
# 1. Open a browser window
# 2. Navigate to each site
# 3. Fill in credentials automatically
# 4. Click login button
# 5. Take screenshots of results
# 6. Save results to artifacts/login-*.png
```

## How It Works

### Flow for Each Site

```
1. Navigate to login URL
   ↓
2. Fill email/username field
   ↓
3. Click Next or Submit
   ↓
4. Fill password field
   ↓
5. Click Login
   ↓
6. Wait for page to load
   ↓
7. Verify success (check URL)
   ↓
8. Screenshot result
```

### Example: LinkedIn Login

```python
# 1. Go to https://www.linkedin.com/login
await page.goto("https://www.linkedin.com/login")

# 2. Fill email
await page.fill("input#username", "your-email@example.com")

# 3. Fill password
await page.fill("input#password", "your-password")

# 4. Click Sign in button
await page.click("button[type='submit']")

# 5. Wait and verify
await asyncio.sleep(5)
if "linkedin.com/feed" in page.url:
    print("✅ Login successful!")
```

## Running Specific Logins

You can also run individual login scripts:

```bash
# Using the CLI
bash solace-browser-cli-v3.sh login linkedin
bash solace-browser-cli-v3.sh login gmail
bash solace-browser-cli-v3.sh login github
bash solace-browser-cli-v3.sh login twitter
```

## Screenshots Generated

After running login automation, check `artifacts/`:

```
artifacts/
├── login-linkedin-success.png      (✅ successful)
├── login-linkedin-attempt.png      (⚠️  partial success)
├── login-linkedin-error.png        (❌ failed)
├── login-gmail-success.png
├── login-github-success.png
└── login-twitter-success.png
```

## Troubleshooting

### "Credentials not configured" error

**Problem**: You haven't added credentials to `credentials.properties`

**Solution**:
```bash
# Edit credentials.properties
nano credentials.properties

# Add your credentials (see Step 1)
```

### Login fails with "Could not find input field"

**Problem**: The website HTML structure changed

**Solution**:
1. Open the site manually in browser
2. Inspect the login form with DevTools
3. Update the CSS selector in the script
4. Example: Change `input#username` to match the actual input ID

### "Multi-factor authentication" required

**Problem**: Site has 2FA enabled

**Status**: Currently not automated (planned for v3.1)

**Workaround**:
1. Disable 2FA temporarily for automation testing
2. Or manually enter 2FA code when prompted

### Password not being filled

**Problem**: Special characters in password

**Solution**: The script auto-escapes special characters. If issues persist:
```python
# Use direct JavaScript instead of fill()
await page.evaluate('''
  document.querySelector("input#password").value = "PASSWORD_HERE"
''')
```

## Security Best Practices

### ✅ DO:
- Keep `credentials.properties` in `.gitignore`
- Use strong, unique passwords
- Use OAuth tokens instead of passwords where possible
- Rotate passwords periodically
- Use environment variables for sensitive data

### ❌ DON'T:
- Commit credentials to git
- Share credentials.properties with others
- Use simple passwords
- Test on production accounts
- Log credentials to files or console

## Advanced Usage

### Recording Login Workflow

```bash
# Record a login as an episode
bash solace-browser-cli-v3.sh record https://linkedin.com my-linkedin-login

# Then use the CLI to navigate and interact
bash solace-browser-cli-v3.sh fill my-linkedin-login "input#username" "email@example.com"
bash solace-browser-cli-v3.sh fill my-linkedin-login "input#password" "password"
bash solace-browser-cli-v3.sh click my-linkedin-login "button[type='submit']"

# Compile and replay
bash solace-browser-cli-v3.sh compile my-linkedin-login
bash solace-browser-cli-v3.sh play my-linkedin-login
```

### Custom Site Login

Add to `credentials.properties`:
```properties
customsite.email=your-email@example.com
customsite.password=your-password
```

Then add login method to `solace_login_automation.py`:
```python
async def login_customsite(self) -> bool:
    # Your custom login logic here
    pass
```

## Tested Sites

| Site | Status | Notes |
|------|--------|-------|
| LinkedIn | ✅ Working | Email/password login |
| Gmail | ✅ Working | Google account + optional 2FA |
| GitHub | ✅ Working | Username/token or password |
| Twitter/X | ✅ Working | Email/password login |
| Facebook | 🔄 In Progress | Cookie-based auth |
| Amazon | 🔄 In Progress | Email verification needed |

## Limitations

- Cannot handle **CAPTCHA** (automated blocking)
- Cannot handle **SMS/Email OTP** (requires 2FA code)
- Cannot handle **Biometric auth** (Face ID, fingerprint)
- Slow sites may timeout (can adjust wait times)

## Performance

Average login times:
- LinkedIn: 8-15 seconds
- Gmail: 10-20 seconds
- GitHub: 5-8 seconds
- Twitter: 10-15 seconds

## Support

For issues:
1. Check troubleshooting section above
2. Review artifact screenshots for errors
3. Check browser logs: `tail logs/browser.log`
4. Verify credentials are correct
5. Test login manually in browser first

---

**Version**: 1.0.0
**Status**: Production Ready for Testing
**Last Updated**: February 14, 2026
