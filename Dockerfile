# Stage 1: Install dependencies
FROM python:3.9-alpine AS builder
WORKDIR /app

RUN apk update && apk add git
RUN git clone --depth 1 --single-branch https://github.com/waladir/script.oneplay.server.git .
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Stage 2: Create the final image
FROM python:3.9-alpine

COPY --from=builder /app/ /app/
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

ENTRYPOINT ["python"]
CMD ["/app/server.py"]

EXPOSE 8082/tcp




############################
# BUILD image tagged as oneplay-server  
# docker build -t oneplay-server .
#
# RUN the container
# docker run -p 8082:8082 -e USERNAME=user -e PASSWORD=pass -e DEVICEID=test -e PORADI_SLUZBY=-1  -e EPG_DNU_ZPETNE=1 -e EPG_DNU_DOPREDU=1 -e INTERVAL_STAHOVANI_EPG=6 -e WEBSERVER_PORT=8082 oneplay-server
