#!/bin/sh
set -e

# ==========
# ENTRYPOINT
# ==========

python3 /app/scripts/wait.py

if [ ! -f /deploy/touched ]; then
    python3 /app/scripts/entrypoint.py
    touch /deploy/touched
fi

touch /etc/certs/gluu-radius.private-key.pem

# run Radius server
exec java \
    -XX:+DisableExplicitGC \
    -XX:+UseContainerSupport \
    -XX:MaxRAMPercentage=$GLUU_MAX_RAM_PERCENTAGE \
    -Dpython.home=/opt/jython \
    -Dlog4j.configurationFile=file:/etc/gluu/conf/radius/gluu-radius-logging.xml \
    -Dradius.home=/opt/gluu/radius \
    -Dradius.base=/opt/gluu/radius \
    -Djava.io.tmpdir=/tmp \
    ${GLUU_JAVA_OPTIONS} \
    -jar /opt/gluu/radius/super-gluu-radius-server.jar \
    -server \
    -config_file /etc/gluu/conf/radius/gluu-radius.properties
