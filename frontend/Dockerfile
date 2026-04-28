# ── Frontend Dockerfile ───────────────────────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /frontend

COPY package.json ./
COPY package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .
RUN npm run build

# ── Production stage (nginx) ──────────────────────────────────────────────────
FROM nginx:stable-alpine AS runtime

COPY --from=builder /frontend/dist /usr/share/nginx/html

# Nginx config: proxy /api/* to the backend service
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
