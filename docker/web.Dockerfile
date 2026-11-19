# Stage 1: build the Vite app
FROM node:22-alpine AS build

# Optional npm mirror override (set NPM_REGISTRY in .env if registry.npmjs.org is unreachable)
ARG NPM_REGISTRY=https://registry.npmjs.org
# Baked in at build time; relative so the browser calls the same domain Caddy serves
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry "${NPM_REGISTRY}" && npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Caddy serves the build output and proxies /api to Django
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile