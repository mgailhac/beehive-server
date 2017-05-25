#!/bin/bash
# Must be run after superuser -i command:
### sudo -i
set -v -x 
echo "STARTING INSTALL..."
date

#TODO: change this to a prompt
#OS="Ubuntu"
OS="CentOS"

#GIT_BRANCH="master"
GIT_BRANCH="wcc-install0"

if [ "${OS}" == "CentOS" ]; then
    APT="yum "
    APT_GET="yum "
else  # Ubuntu
    APT="apt "
    APT_GET="apt-get "
fi



function RETRY_UNTIL_SUCCEED() { 
    until $*; 
    do echo "FAILED.  Waiting to retry...     " `date`
    sleep 20
    done; 
}



echo "APT = " ${APT}
echo "APT_GET = " ${APT_GET}


if true; then
    if true; then
        #####################################################################
        #########   UN-INSTALL old beehive server
        #####################################################################
        echo "WARNING:  You are about to UNINSTALL the beehive!!!!"
        echo -n  "Are you sure? ('Yes' to continue) > "
        read confirmation
        echo confirmation = "$confirmation"
        if [ "$confirmation" == "Yes" ]; then
            set -v -x
            echo "UN-INSTALLing beehive..."
            ## files in $DATE=/mnt
            rm -rf /mnt/cassandra  /mnt/mysql  /mnt/rabbitmq  /mnt/ssh_keys  /mnt/waggle

            ##-- systemd
            cd /etc/systemd/system
            for s in $(systemctl list-units --plain '*beehive*' | grep beehive | awk '{print $1}'); do
                systemctl stop $s
                systemctl disable $s
                systemctl reset-failed $s
            done
            rm -f /etc/systemd/system/*beehive-*.service

            systemctl status beehive-*  --no-pager -l
            systemctl list-units 'beehive-*' --all
            systemctl daemon-reload

            ##-- docker containers
            echo "BEFORE removal...."
            docker ps -a
            for container in `docker ps -aq`; do
                echo ' removing container ' $container
                docker rm -fv $container
            done
            for image in `docker images -aq`; do
                echo ' removing container image ' $image
                docker rmi -f $image
            done
            
            bash /root/git/beehive-server/scripts/docker_cleanup.sh
            
            echo "AFTER removal...."
            docker ps -a
            docker images -a
            docker volume ls
            service docker stop
            rm -rf /var/lib/docker/aufs

            echo "UNInstall COMPLETE."
        else
            echo "Uninstall ABORTed."
        fi
    fi
    #####################################################################
    #########   INSTALL
    #####################################################################

    RETRY_UNTIL_SUCCEED  ${APT} update -y
    RETRY_UNTIL_SUCCEED  ${APT_GET} install -y curl
    RETRY_UNTIL_SUCCEED  ${APT_GET} install -y git
    
    cd /root
    rm -rf git
    mkdir -p git
    cd git
    RETRY_UNTIL_SUCCEED git clone https://github.com/waggle-sensor/beehive-server.git
    cd /root/git/beehive-server/
    git checkout ${GIT_BRANCH}

    # beehive-config.json
    mkdir -p /mnt/beehive
    cp -i install/beehive-config.json /mnt/beehive
    echo; echo; echo "*** YOU MUST edit /mnt/beehive/beehive-config.json specific to this beehive server"
    echo " If you have not customized this file yet, go do it now."
    echo " If you have customized this file, and want to continue, enter 'Yes'."
    read confirmation
    echo confirmation = "$confirmation"
    if [ "$confirmation" != "Yes" ]; then
        exit
    fi
    
    # NGINX needs SSL keys
    echo; echo; echo "NGINX SSL keys need the following information..."
    cd /root/git/beehive-server/beehive-nginx
    make ssl
    echo "NGINX SSL keys created"
    echo; echo
    
    # ssl keys should be copied or generated into '/usr/lib/waggle/ssh_keys/id_rsa_waggle_aot_registration.pub'
    
    
    #### Docker
    if [ "${OS}" == "CentOS" ]; then
        curl -sSL https://get.docker.com/ | sh
    else
        RETRY_UNTIL_SUCCEED apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
        export CODENAME=$(lsb_release --codename | grep -o "[a-z]*$" | tr -d '\n')
        echo "deb https://apt.dockerproject.org/repo ubuntu-${CODENAME} main" > /etc/apt/sources.list.d/docker.list
        RETRY_UNTIL_SUCCEED apt-get update
        RETRY_UNTIL_SUCCEED apt-get install -y  docker-engine
    fi
    RETRY_UNTIL_SUCCEED service docker restart
    RETRY_UNTIL_SUCCEED docker --version

    export DATA="/mnt"
    echo "export DATA=/mnt/" >> /root/.bash_profile
    docker network create beehive

    docker network ls
    docker network inspect beehive

    #apt-get install -y python-webpy

    # pull all the images we have in the docker hub 
    #  - commented out because "docker build" should automatically pull any "FROM" containers
    
    # docker pull cassandra:3.2
    # docker pull mysql:5.7.10
    # docker pull rabbitmq:3.5.6
    # docker pull waggle/beehive-server:latest
    
    # build all the images that need to be built
    for a in \
        /root/git/beehive-server/beehive-cert/                      \
        /root/git/beehive-server/beehive-flask/                     \
        /root/git/beehive-server/beehive-nginx/                     \
        /root/git/beehive-server/beehive-plenario-sender/           \
        /root/git/beehive-server/beehive-queue-to-mysql/            \
        /root/git/beehive-server/beehive-sshd/                      \
        /root/git/beehive-server/beehive-rabbitmq/                  \
        /root/git/beehive-server/data-pipeline/workers/gps-sense/   \
        /root/git/beehive-server/data-pipeline/workers/alphasense/  \
        /root/git/beehive-server/data-pipeline/workers/coresense/
    do
        echo
        echo $a
        cd $a
        make build
    done
    
    ### SSL
    [ ! -z "$DATA" ] && docker run -ti \
      --name certs \
      --rm \
      -v ${DATA}/waggle/SSL/:/usr/lib/waggle/SSL/ \
      waggle/beehive-server:latest ./SSL/create_certificate_authority.sh

    ### RabbitMQ - this must run BEFORE RabbitMQ container is up
    mkdir -p ${DATA}/rabbitmq/config/ && \
    #curl https://raw.githubusercontent.com/waggle-sensor/beehive-server/master/beehive-rabbitmq/rabbitmq.config > ${DATA}/rabbitmq/config/rabbitmq.config
    cp /root/git/beehive-server/beehive-rabbitmq/rabbitmq.config  ${DATA}/rabbitmq/config/
    
    [ ! -z "$DATA" ] && docker run -ti \
      --name certs \
      --rm \
      -v ${DATA}/waggle/SSL/:/usr/lib/waggle/SSL/ \
      waggle/beehive-server:latest ./SSL/create_server_cert.sh

    chmod +x ${DATA}/waggle/SSL/server

    ### systemd  - start all the services once the containers are available
    cd /root/git/beehive-server/systemd/

    for service in beehive-*.service ; do
        echo "store and enable service:   ${service}"
        rm -f /etc/systemd/system/${service}
        cp ${service} /etc/systemd/system
        systemctl daemon-reload
        systemctl enable ${service}
    done
    
    for service in beehive-*.service ; do
        echo "start ${service}"
        systemctl start ${service}
        systemctl status ${service}  --no-page -l
        sleep 3
    done
    
    sleep 10
    
    systemctl status '*beehive*'  --no-page -l
    systemctl list-units -a '*beehive*'
    
    date

    # after beehive-mysql is running
    while true; do
        #curl https://raw.githubusercontent.com/waggle-sensor/beehive-server/master/beehive-mysql/createTablesMysql.sql | docker exec -i beehive-mysql mysql -u waggle --password=waggle && break
        cat /root/git/beehive-server/beehive-mysql/createTablesMysql.sql | docker exec -i beehive-mysql mysql -u waggle --password=waggle \
        && break

      sleep 10
      nTries=$[$nTries+1]
      echo "  mysql try #" $nTries " ..."
    done
    
    # after beehive-cassandra is running
    sleep 20
    while true; do
        # curl https://raw.githubusercontent.com/waggle-sensor/beehive-server/master/beehive-cassandra/createTablesCassandra.sql | docker exec -i beehive-cassandra cqlsh && break
        
        cat /root/git/beehive-server/beehive-cassandra/createTablesCassandra.sql | docker exec -i beehive-cassandra cqlsh \
        && break
        
      sleep 10
      nTries=$[$nTries+1]
      echo "  mysql try #" $nTries " ..."
    done

    
    # after beehive-rabbitmq is up
    nTries=0
    sleep 20
    while true
    do docker exec -ti  beehive-rabbitmq bash -c '\
            bash /usr/lib/waggle/beehive-server/beehive-rabbitmq/rabbitmqInit.bash' \
            && break
            
            # rabbitmq-plugins enable rabbitmq_management rabbitmq_auth_mechanism_ssl ; \
            # curl localhost:15672/cli/rabbitmqadmin > /usr/bin/rabbitmqadmin ; \
            # chmod 777 /usr/bin/rabbitmqadmin ; \
            # rabbitmqctl add_user waggle waggle  ; \
            # rabbitmqctl set_user_tags waggle administrator  ; \
            # rabbitmqctl add_user node waggle  ; \
            # rabbitmqctl add_user server waggle  ; \
            # rabbitmqctl set_permissions node "node_.*" ".*" ".*"  ; \
            # rabbitmqctl set_permissions server ".*" ".*" ".*"  ;' \
            
      sleep 10
      nTries=$[$nTries+1]
      echo "rabbitmqctl try #" $nTries " ..."
    done
fi 

echo "FINISHING INSTALL..."
date
echo 'DONE'
date
