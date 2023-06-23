# Build the venv
FROM python:3-bookworm as build

WORKDIR /opt

COPY scripts/mobileraker-requirements.txt .
RUN python -m venv venv \
 && venv/bin/pip install -r mobileraker-requirements.txt

# Runtime Image
FROM python:3-slim-bookworm

RUN apt update \
 && apt install -y \
      git \
      zlib1g \
      libtiff6 libjpeg62-turbo libopenjp2-7 \
 && apt clean

WORKDIR /opt
RUN groupadd mobileraker --gid 1000 \
 && useradd mobileraker --uid 1000 --gid mobileraker
RUN mkdir -p printer_data/config \
 && chown -R mobileraker:mobileraker /opt/*

COPY --chown=mobileraker:mobileraker --from=build /opt/venv venv
COPY --chown=mobileraker:mobileraker . mobileraker

USER mobileraker
VOLUME ["/opt/printer_data/config"]
ENTRYPOINT ["venv/bin/python", "mobileraker/mobileraker.py"]
CMD ["-c", "printer_data/config/mobileraker.conf"]