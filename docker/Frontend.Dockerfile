#FROM nginx:1.21
FROM nginx

COPY ./frontend/dist /usr/share/nginx/html/

RUN chown -R www-data:www-data /usr/share/nginx/html && \
    find /usr/share/nginx/html -type f -exec chmod o+r {} \; && \
    find /usr/share/nginx/html -type d -exec chmod o+rx {} \;

WORKDIR /usr/share/nginx/html/
