ARG PYTHON_VERSION=3.14

FROM python:${PYTHON_VERSION}-alpine

WORKDIR /app

# 1. Copy application code
COPY . /app/

# 2. Install Python dependencies
RUN pip install --no-cache-dir --no-warn-script-location --root-user-action=ignore -r /app/requirements.txt

# 3. Create non-root user and set ownership
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && \
    chown -R appuser:appgroup /app
USER appuser

# Set the entry point and default command
ENTRYPOINT ["python"]
CMD ["/app/server.py"]

EXPOSE 8082/tcp


############################
# BUILD image tagged as oneplay-server  
# docker build -t oneplay-server .
#
# RUN the container
# docker run -p 8082:8082 -e USERNAME=user -e PASSWORD=pass -e DEVICEID=test -e PORADI_SLUZBY=-1  -e EPG_DNU_ZPETNE=1 -e EPG_DNU_DOPREDU=1 -e INTERVAL_STAHOVANI_EPG=6 -e WEBSERVER_PORT=8082 oneplay-server
