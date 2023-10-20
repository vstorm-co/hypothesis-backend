FROM nginx:stable-alpine

# Copy the build output from Vite to the Nginx HTML directory
COPY ./frontend/dist /usr/share/nginx/html/

# Copy your custom Nginx configuration file into the container
COPY ./docker/nginx/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
