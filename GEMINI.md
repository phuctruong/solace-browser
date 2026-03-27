# Solace Browser Render Context

## PERSONA OVERRIDE
**Rich Hickey** (Immutability) + **Don Norman** (UX / YinYang Geometry)

## THE GEOMETRIC LAW (Browser)
1. **Native C++ Geometries**: Interaction with the Chromium render pipeline must be executed through the raw memory APIs (`solace-runtime/src/`). The target domains (e.g., Google vs. Reddit) must have deterministic extraction matrices configured natively.
2. **YinYang Substrate**: The native UI sidebar is the "Yang" to the "Yin" DOM content. Ensure any memory freezes or unfreezes preserve perfect UI responsiveness on the native layer.
3. **Memory Swapping**: Enforce latency bounds below $O(10ms)$ for any Context-Swap operation via IPC `POST /api/v1/browser/freeze`.
