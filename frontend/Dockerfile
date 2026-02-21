# ========== 第一阶段：构建 Vue 前端 ==========
FROM node:20-alpine AS builder

WORKDIR /app

# 复制 package 文件
COPY package.json package-lock.json* ./

# 安装依赖（使用国内镜像可加速，可选）
RUN npm ci

# 复制源码并构建
COPY . .
RUN npm run build

# ========== 第二阶段：使用 Nginx 提供静态文件 ==========
FROM nginx:alpine

# 复制构建产物到 Nginx 默认静态目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
