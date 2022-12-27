FROM alphaceti/default-python:0.2.0 as base
ENV PROMETHEUS_MULTIPROC_DIR="/usr/src/app/prometheus" \
    PATH="${PATH}:/home/jimmy/.local/bin"
ADD app /usr/src/app
RUN apk add --update --no-cache libtorrent gcompat openssl-dev && \
    apk upgrade && \
    addgroup -S jimmy && \
    adduser -h /home/jimmy -S jimmy -G jimmy && \
    chmod +x /usr/src/app/* && \
    chown -R jimmy:jimmy /usr/src/app
EXPOSE 5000/tcp
USER jimmy
WORKDIR /usr/src/app
RUN pip3 install -r ./requirements.txt
CMD [ "./entry.sh" ]
