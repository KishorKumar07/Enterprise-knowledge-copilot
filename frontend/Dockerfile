# Multi-stage build. The runtime stage copies only Next's standalone output, so
# the final image doesn't carry the toolchain or dev dependencies.
# Node 22 (LTS) rather than 24 — Next 16 supports both, and LTS is the safer
# base for something long-running.

# ---- deps: install into a cacheable layer keyed on the lockfile ----
FROM node:22-alpine AS deps
WORKDIR /app
# Optional extra root CA for local builds on a network that re-signs HTTPS
# (e.g. Avast Web Shield), which otherwise breaks npm with
# UNABLE_TO_VERIFY_LEAF_SIGNATURE. Drop a .crt into frontend/.local-ca/ (gitignored).
# With no .crt there — CI, the server — this is a no-op and TLS stays strict.
COPY .local-ca /local-ca
RUN cat /local-ca/*.crt > /extra-ca.pem 2>/dev/null || true
COPY package.json package-lock.json ./
RUN if [ -s /extra-ca.pem ]; then export NODE_EXTRA_CA_CERTS=/extra-ca.pem; fi; npm ci

# ---- builder: compile the app ----
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* values are inlined into the client bundle by `next build`, so
# they must be present as build args here. Passing them only at runtime leaves
# the fallbacks compiled in, and every browser request goes to the wrong host.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_GRAFANA_URL
ARG NEXT_PUBLIC_PHOENIX_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_GRAFANA_URL=$NEXT_PUBLIC_GRAFANA_URL
ENV NEXT_PUBLIC_PHOENIX_URL=$NEXT_PUBLIC_PHOENIX_URL

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---- runner: standalone output only ----
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN addgroup -g 1001 -S nodejs && adduser -u 1001 -S nextjs -G nodejs

# public/ and .next/static aren't bundled into standalone — they're copied in
# alongside it, at the paths server.js expects.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

# standalone emits its own minimal server; `next start` isn't available here.
CMD ["node", "server.js"]
