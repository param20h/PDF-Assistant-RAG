# syntax=docker/dockerfile:1
# =============================================================================
# Multi-stage Dockerfile for the PDF-Assistant-RAG Next.js frontend.
#
# next.config.ts uses output: "export" which generates a fully static site
# under /out — no Node.js runtime is needed at serve time. The final image
# uses nginx:alpine to serve the static assets, eliminating all node_modules
# and dev dependencies from the production image.
#
# Stages:
#   deps     — install production + dev deps from lockfile (cached layer)
#   builder  — run `next build` to produce the static /out directory
#   runner   — nginx:alpine serving /out; no Node.js, no node_modules
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — deps: install dependencies from lockfile
# -----------------------------------------------------------------------------
FROM node:20-alpine AS deps

# Check https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine
# for why libc6-compat may be needed.
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy only the manifests first so this layer is cached unless deps change
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# -----------------------------------------------------------------------------
# Stage 2 — builder: compile the Next.js static export
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

RUN apk add --no-cache libc6-compat

WORKDIR /app

# Restore installed modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy full source
COPY . .

# next build reads NEXT_PUBLIC_* vars at build time — pass them as ARGs so
# CI/CD pipelines can inject the correct API URL without baking it into the
# image unconditionally.
ARG NEXT_PUBLIC_API_URL=http://localhost:7860
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

# Disable Next.js telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Produce the static export in /app/out
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 3 — runner: nginx serves the static export
# No Node.js, no node_modules, no source code in this image.
# -----------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runner

# Remove the default nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled static assets from builder
COPY --from=builder /app/out /usr/share/nginx/html

# Custom nginx config:
#   - try_files for SPA-style client-side routing fallback
#   - gzip compression for JS/CSS/HTML
#   - cache headers for static assets
COPY nginx.conf /etc/nginx/conf.d/default.conf

# nginx runs as root by default; drop to a non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser  -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown appuser:appgroup /var/run/nginx.pid

USER appuser

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
