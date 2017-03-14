FROM rabbitmq:3.5.6

COPY ./enabled_plugins /etc/rabbitmq/enabled_plugins
COPY ./rabbitmq.config /etc/rabbitmq/rabbitmq.config

RUN apt-get update && apt-get install -y python
RUN curl localhost:15672/cli/ > /usr/bin/rabbitmqadmin
RUN chmod 777 /usr/bin/rabbitmqadmin

