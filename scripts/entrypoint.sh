#!/bin/sh
set -e

run_entrypoint() {
    if [ ! -f /deploy/touched ]; then
        python /app/scripts/entrypoint.py
        touch /deploy/touched
    fi
}

# ==========
# ENTRYPOINT
# ==========

cat << LICENSE_ACK

# ================================================================================================ #
# Gluu License Agreement: https://github.com/GluuFederation/enterprise-edition/blob/4.0.0/LICENSE. #
# The use of Gluu Server Enterprise Edition is subject to the Gluu Support License.                #
# ================================================================================================ #

LICENSE_ACK

if [ -f /etc/redhat-release ]; then
    source scl_source enable python27 && python /app/scripts/wait.py
    source scl_source enable python27 && run_entrypoint
else
    python /app/scripts/wait.py
    run_entrypoint
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
    -jar /opt/gluu/radius/super-gluu-radius-server.jar \
    -server \
    -config_file /etc/gluu/conf/radius/gluu-radius.properties
