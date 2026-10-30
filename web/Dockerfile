# Build context is the repo root so docs/about/ can be imported without
# copying the prose into web/ (ADR 0024, issue #41).
FROM node:22-alpine AS build

WORKDIR /repo/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY docs/about /repo/docs/about
RUN npm run build

FROM nginx:1.27-alpine

COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/web/dist /usr/share/nginx/html
