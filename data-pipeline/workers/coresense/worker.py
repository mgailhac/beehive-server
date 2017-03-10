#!/usr/bin/env python3
import os.path
import pika
import ssl
from waggle.coresense.utils import decode_frame
from urllib.parse import urlencode
import json


plugin = 'coresense:3'

credentials = pika.PlainCredentials('worker_coresense', 'waggle')
parameters = pika.ConnectionParameters('beehive-rabbitmq', credentials=credentials)
connection = pika.BlockingConnection(parameters)
print('connected to RabbitMQ')

channel = connection.channel()

channel.exchange_declare(exchange='plugins-in',
                         exchange_type='direct')

channel.exchange_bind(source='data-pipeline-in',
                      destination='plugins-in')

channel.queue_declare(queue=plugin,
                      durable=True)

channel.queue_bind(queue=plugin,
                   exchange='plugins-in',
                   routing_key=plugin)

channel.exchange_declare(exchange='plugins-out',
                         exchange_type='fanout',
                         durable=True)


def callback(ch, method, properties, body):
    for sensor, values in decode_frame(body).items():
        props = pika.BasicProperties(
            app_id=properties.app_id,
            timestamp=properties.timestamp,
            reply_to=properties.reply_to,
            type=sensor,
            content_type='text/json',
        )

        channel.basic_publish(properties=props,
                              exchange='plugins-out',
                              routing_key=method.routing_key,
                              body=json.dumps(values))

    ch.basic_ack(delivery_tag=method.delivery_tag)


channel.basic_consume(callback, queue=plugin, no_ack=False)
channel.start_consuming()
