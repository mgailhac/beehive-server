data = /mnt
image = waggle/beehive-cert
container = beehive-cert

build:
    docker build -t $(image) .

start:
    systemctl start $(container)

stop:
    systemctl stop $(container)

restart:
    systemctl restart $(container)

logs:
    journalctl -f -u $(container)

clean:
    docker rm -f $(container)
    docker rmi -f $(image)

run:
    docker run \
        --log-driver=journald \
        --ti \
        -rm \
        -p 24181:80 \
        -v $(data)/ssh_keys/:/usr/lib/waggle/ssh_keys/ \
        -v $(data)/waggle/SSL/:/usr/lib/waggle/SSL/ \
        --name $(container) \
        --net beehive \
        $(image) /bin/bash -c 'cd /usr/lib/waggle/beehive-server/beehive-cert ; git pull ; ./cert-serve.py'
