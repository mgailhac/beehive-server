for UNAME in            \
    last_data           \
    last_log            \
    node                \
    queue_to_db_decoded \
    queue_to_db_raw     \
    server              \
    worker_alphasense   \
    worker_coresense    \
    worker_gps
do echo $UNAME
    # declare user name=... password=... tags=...
    rabbitmqadmin declare user name=$UNAME password=waggle tags=""
    
    # declare permission vhost=... user=... configure=... write=... read=...
    rabbitmqadmin declare permission user=$UNAME vhost="/" configure=".*" write=".*" read=".*"
    
    rabbitmqctl list_user_permissions $UNAME
done
rabbitmqctl list_users

# NOTE: This is where we declare all exchanges, queues and bindings EXCEPT FOR the queues and bindings 
# specific to plugins / decoders - because these are more dynamic - and likely to change throughout the
# lifetime of a beehive server.

# declare exchange name=... type=... [auto_delete=... internal=... durable=... arguments=...]
rabbitmqadmin declare exchange name=data-pipeline-in  type=fanout   durable=true
rabbitmqadmin declare exchange name=images            type=fanout   durable=true
rabbitmqadmin declare exchange name=logs              type=fanout   durable=true
rabbitmqadmin declare exchange name=plugins-in        type=direct   durable=true
rabbitmqadmin declare exchange name=plugins-out       type=fanout   durable=true

# declare queue name=... [node=... auto_delete=... durable=... arguments=...]
rabbitmqadmin declare queue name=plenario   durable=true
rabbitmqadmin declare queue name=last-log   durable=true
rabbitmqadmin declare queue name=last-data  durable=true
rabbitmqadmin declare queue name=db-raw     durable=true
rabbitmqadmin declare queue name=db-decoded durable=true

# declare binding source=... destination=... [arguments=... routing_key=... destination_type=...]
rabbitmqadmin declare binding source=data-pipeline-in destination=plugins-in destination_type=exchange
rabbitmqadmin declare binding source=data-pipeline-in destination=last-data  destination_type=queue
rabbitmqadmin declare binding source=logs             destination=last-log   destination_type=queue
rabbitmqadmin declare binding source=plugins-out      destination=plenario   destination_type=queue
rabbitmqadmin declare binding source=data-pipeline-in destination=db-raw     destination_type=queue
rabbitmqadmin declare binding source=plugins-out      destination=db-decoded destination_type=queue


#  declare vhost name=... [tracing=...]
#  declare policy name=... pattern=... definition=... [priority=... apply-to=...]
#  declare parameter component=... name=... value=...
#  declare permission vhost=... user=... configure=... write=... read=...
