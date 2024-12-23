# Stage 1: Building the code
FROM node:23-alpine AS builder

WORKDIR /app

# Enable corepack and use correct Yarn version
RUN corepack enable && corepack prepare yarn@4.5.3 --activate

# Copy package files first
COPY package.json yarn.lock .yarnrc.yml ./
RUN yarn install --immutable

# Copy source code
COPY . .

# Build application
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN yarn build

# Stage 2: Production image
FROM node:23-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy necessary files from builder
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Create non-root user and set permissions in one layer
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
