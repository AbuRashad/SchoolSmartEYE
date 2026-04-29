# ── Frontend Dockerfile ───────────────────────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /frontend

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

# ── Production stage (nginx) ──────────────────────────────────────────────────
FROM nginx:stable-alpine AS runtime

COPY --from=builder /frontend/dist /usr/share/nginx/html

# Nginx config: proxy /api/* to the backend service
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
