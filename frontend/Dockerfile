FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json ./
RUN npm install

COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine

RUN apk add --no-cache apache2-utils

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/docker-entrypoint.d/10-basic-auth.sh /docker-entrypoint.d/10-basic-auth.sh
RUN chmod +x /docker-entrypoint.d/10-basic-auth.sh
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
