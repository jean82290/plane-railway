# Plane's official proxy image with a Caddyfile that routes to Railway
# private domains instead of Docker Compose service names.
ARG PLANE_VERSION=v1.4.2
FROM makeplane/plane-proxy:${PLANE_VERSION}

COPY proxy/Caddyfile /etc/caddy/Caddyfile
