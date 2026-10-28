# Build the React page, then serve the static files. nginx proxies /api
# to the Compose service `api`, so the browser stays on one origin (ADR 0021).
FROM node:22-alpine AS build

WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
