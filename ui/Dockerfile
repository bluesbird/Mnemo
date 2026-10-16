FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig*.json vite.config.mts index.html ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/default.conf.template /opt/mnemo/default.conf.template
COPY docker/start.sh /opt/mnemo/start.sh
RUN sed -i 's/\r$//' /opt/mnemo/start.sh
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
ENTRYPOINT ["/bin/sh", "/opt/mnemo/start.sh"]
CMD ["nginx", "-g", "daemon off;"]
