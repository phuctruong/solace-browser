# Prime Mermaid: wave6-live.example.com

- Site: `wave6-live.example.com`
- Auth: unknown (discovered baseline)
- Page types: home, auth, dashboard, settings

```mermaid
flowchart TD
  HOME[Home] --> AUTH[Auth]
  AUTH --> DASH[Dashboard]
  DASH --> SETTINGS[Settings]
```

## Selector Seeds
- login_button: "button[type=submit]"
- nav_links: "a[href]"
