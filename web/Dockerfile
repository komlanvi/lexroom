FROM node:26.13.0-slim AS build

RUN npm install --global pnpm@12.18.0
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# Dependencies first, so code changes reuse this layer.
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM node:26.13.0-slim

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app

COPY --from=build --chown=node /app/.next/standalone ./
COPY --from=build --chown=node /app/.next/static ./.next/static
USER node

EXPOSE 3000
# API_URL (the backend's address) is read at request time by the /api proxy.
CMD ["node", "server.js"]
