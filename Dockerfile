# syntax=docker/dockerfile:1

# ============================================================================
# Build Stage: Compile Solace Browser (Ungoogled Chromium)
# ============================================================================
FROM debian:bookworm-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ninja-build \
    pkg-config \
    git \
    python3 \
    python3-distutils \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Build directory
WORKDIR /build

# Note: In production, you would either:
# A) Copy pre-compiled binary from /home/phuc/projects/solace-browser/out/Release/chrome
# B) Clone and compile ungoogled-chromium here (~3-4 hours)
#
# For Cloud Run deployment, we use option A (pre-compiled binary).
# The Dockerfile is structured for both approaches.

# ============================================================================
# Runtime Stage: Minimal container with compiled Solace Browser
# ============================================================================
FROM debian:bookworm-slim

LABEL maintainer="Solace Browser Team"
LABEL description="Solace Browser - Privacy-focused browser automation for Cloud Run"
LABEL version="2.0.0"

# Install minimal runtime dependencies (only what Chromium needs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libindicator7 \
    libgconf-2-4 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libasound2 \
    libpulse0 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libexpat1 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxkbcommon0 \
    libxshmfence1 \
    python3-minimal \
    python3-pip \
    node-typescript \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy HTTP server (Node.js wrapper)
COPY http_server.js /app/http_server.js
COPY package.json /app/package.json
COPY package-lock.json* /app/package-lock.json

# Copy Python HTTP bridge
COPY http_bridge.py /app/http_bridge.py
COPY requirements.txt /app/requirements.txt

# Install Node.js dependencies (production only)
RUN npm ci --only=production && npm cache clean --force

# Install Python dependencies
RUN pip install --no-cache-dir \
    -r /app/requirements.txt

# Copy pre-compiled Solace Browser binary from build context
# Expecting binary at /home/phuc/projects/solace-browser/out/Release/chrome
COPY --from=builder /build/out/Release/chrome /usr/local/bin/solace-browser 2>/dev/null || \
    echo "Note: Binary not found in build context. Expecting binary to be mounted at runtime."

# Fallback: If using pre-built binary, copy directly:
# COPY out/Release/chrome /usr/local/bin/solace-browser

# Set permissions
RUN chmod +x /usr/local/bin/solace-browser || true

# Create runtime directories
RUN mkdir -p /app/logs /app/artifacts /app/recipes /app/episodes

# Set environment variables
ENV PORT=8080 \
    NODE_ENV=production \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99

# Expose Cloud Run port
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=2 \
    CMD node -e "require('http').get('http://localhost:${PORT}/health', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})" || exit 1

# Set user for security (non-root)
RUN useradd -m -u 1000 -s /bin/bash solace && \
    chown -R solace:solace /app

USER solace

# Start HTTP API server
# The server will spawn Solace Browser processes as needed
CMD ["node", "/app/http_server.js"]
