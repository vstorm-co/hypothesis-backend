#FROM nginx:1.19.0-alpine
#FROM nginx:alpine:3.14
FROM nginx

EXPOSE 80

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d
