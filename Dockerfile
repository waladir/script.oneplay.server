ARG PYTHON_VERSION=3.12

# Stage 1: Build a dedicated environment with dependencies
FROM python:${PYTHON_VERSION}-alpine AS builder
WORKDIR /app

# 1. Upgrade pip (as root, this is generally fine)
RUN pip install --upgrade pip --root-user-action=ignore

# 2. Install git and create the non-root user 'appuser'
RUN apk add --no-cache git
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# 3. Clone the repository (as root) and set ownership for appuser
RUN git clone --depth 1 --single-branch https://github.com/waladir/script.oneplay.server.git .
RUN chown -R appuser:appgroup /app

# 4. Switch user to 'appuser'
USER appuser

# 5. Install Python dependencies as the non-root user.
# The following flags suppress warnings:
# --no-warn-script-location: Suppresses warning about scripts not being on PATH.
# --no-cache-dir: Optimizes image size.
RUN pip install --no-cache-dir --no-warn-script-location -r /app/requirements.txt

# ----------------------------------------------------------------------------------

# Stage 2: Create the minimal final image
FROM python:${PYTHON_VERSION}-alpine

WORKDIR /app

# 1. Recreate the same non-root user in the final image
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# 2. Copy the application code
COPY --from=builder --chown=appuser:appgroup /app/ /app/

# 3. Copy packages from the 'appuser' local installation path to the same local path.
# This ensures the non-root user can access the libraries.
COPY --from=builder /home/appuser/.local /home/appuser/.local

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
