
FROM waggle/beehive-server

# RUN apt-get update && apt-get install -y python-mysqldb


########################################################
######################################################
RUN apt-get update && apt-get install -y \
    python-mysqldb ##################\
    python3-dev \
    python3-pip \
    libmysqlclient-dev

# python modules
# Note regarding the mysql library (mysqlclient is a replacement for MySQL-python which has some python3 issues)

RUN pip3 install \
    git+https://github.com/waggle-sensor/pywaggle
######################################################
######################################################

EXPOSE 80
WORKDIR /usr/lib/waggle/beehive-server/beehive-cert/
