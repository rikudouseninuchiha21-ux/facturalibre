# syntax=docker/dockerfile:1

FROM node:20-alpine AS base
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install --global pnpm@10.34.7
WORKDIR /app

# Dependencias completas compartidas por desarrollo y build.
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Etapa de desarrollo usada por docker-compose.override.yml.
FROM deps AS dev
ARG BACKEND_INTERNAL_URL=http://backend:8000
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}
ENV NODE_ENV=development
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]

# Etapa de compilación de producción.
FROM deps AS builder
ARG BACKEND_INTERNAL_URL=http://127.0.0.1:8000
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}
COPY . .
RUN pnpm build

# Solo dependencias de producción para la imagen final.
FROM base AS prod-deps
ENV NODE_ENV=production
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --prod

FROM node:20-alpine AS runner
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

COPY --from=prod-deps --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nodejs /app/next.config.mjs ./next.config.mjs

USER nextjs
EXPOSE 3000

CMD ["node", "node_modules/next/dist/bin/next", "start"]
