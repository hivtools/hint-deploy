FROM alpine

RUN apt-get update && apt-get -y install --no-install-recommends \
    openssh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

CMD [ "bash" ]
