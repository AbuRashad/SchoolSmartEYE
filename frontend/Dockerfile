# ── Frontend Dockerfile ───────────────────────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /workspace

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
RUN npm ci

COPY frontend ./frontend
RUN npm run build --workspace frontend

# ── Production stage (nginx) ──────────────────────────────────────────────────
FROM nginx:stable-alpine AS runtime

COPY --from=builder /workspace/frontend/dist /usr/share/nginx/html

# Nginx config: proxy /api/* to the backend service
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
