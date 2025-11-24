# Dev stage（用掛載，不複製源碼）
FROM node:20-slim as dev
WORKDIR /app
# 只複製 package.json 安裝依賴，源碼用掛載
COPY package*.json ./
RUN npm install
# 不 COPY 源碼，由 docker-compose volumes 掛載
CMD ["npm", "run", "dev", "--", "--host"]

# Build stage
FROM node:20-slim as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
