FROM nginx:alpine

# Copy nginx configuration
COPY docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Create directory for certificates
RUN mkdir -p /etc/nginx/certs

# Expose HTTPS port
EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]

