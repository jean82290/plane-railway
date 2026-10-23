# Plane backend for Railway: the API, the Celery worker and the Celery beat
# scheduler all run from this image, chosen by the PLANE_ROLE variable.
#
# The official image is used unmodified; this only adds the Railway start-up
# scripts. PLANE_VERSION is passed by Railway as a build argument.
ARG PLANE_VERSION=v1.4.2
FROM makeplane/plane-backend:${PLANE_VERSION}

COPY backend/railway/ /railway/
RUN chmod +x /railway/start.sh

CMD ["/railway/start.sh"]
