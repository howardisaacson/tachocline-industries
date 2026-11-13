# Build context is the repo root so docs/about/ can be imported without
# copying the prose into web/ (ADR 0024, issue #41).
# Pin the Oct 2026 security release (issue #75).
# https://nodejs.org/en/blog/vulnerability/october-2026-security-releases
# linux/amd64 and linux/arm64/v8, checked 2026-11-13. No platform pin.
FROM node:22.23.4-alpine AS build

WORKDIR /repo/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY docs/about /repo/docs/about
COPY docs/data-science-workflow.md /repo/docs/data-science-workflow.md
COPY docs/data-links.md /repo/docs/data-links.md
RUN npm run build

# linux/amd64 and linux/arm64/v8, checked 2026-11-13.
FROM nginx:1.27-alpine

COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/web/dist /usr/share/nginx/html
