FROM openjdk:8-jre-alpine3.9

# ===============
# Alpine packages
# ===============

RUN apk update && apk add --no-cache \
    wget \
    unzip \
    py-pip \
    openssl \
    git

# ======
# Radius
# ======

ENV GLUU_VERSION=4.0.0-SNAPSHOT \
    GLUU_BUILD_DATE=2019-09-08

RUN mkdir -p /opt/gluu/radius \
    && wget -q https://ox.gluu.org/maven/org/gluu/super-gluu-radius-server/${GLUU_VERSION}/super-gluu-radius-server-${GLUU_VERSION}.jar -O /opt/gluu/radius/super-gluu-radius-server.jar \
    && wget -q https://ox.gluu.org/maven/org/gluu/super-gluu-radius-server/${GLUU_VERSION}/super-gluu-radius-server-${GLUU_VERSION}-distribution.zip -O /tmp/gluu-radius-libs.zip \
    && unzip -n -q /tmp/gluu-radius-libs.zip -d /opt/gluu/radius \
    && rm /tmp/gluu-radius-libs.zip

# Radius ports
EXPOSE 1812/udp 1813/udp

# ====
# Tini
# ====

RUN wget -q https://github.com/krallin/tini/releases/download/v0.18.0/tini-static -O /usr/bin/tini \
    && chmod +x /usr/bin/tini

# ======
# Python
# ======

COPY requirements.txt /tmp/requirements.txt
RUN pip install -U pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && apk del git

# =======
# License
# =======

RUN mkdir -p /licenses
COPY LICENSE /licenses/

# ==========
# Config ENV
# ==========

ENV GLUU_CONFIG_ADAPTER=consul \
    GLUU_CONFIG_CONSUL_HOST=localhost \
    GLUU_CONFIG_CONSUL_PORT=8500 \
    GLUU_CONFIG_CONSUL_CONSISTENCY=stale \
    GLUU_CONFIG_CONSUL_SCHEME=http \
    GLUU_CONFIG_CONSUL_VERIFY=false \
    GLUU_CONFIG_CONSUL_CACERT_FILE=/etc/certs/consul_ca.crt \
    GLUU_CONFIG_CONSUL_CERT_FILE=/etc/certs/consul_client.crt \
    GLUU_CONFIG_CONSUL_KEY_FILE=/etc/certs/consul_client.key \
    GLUU_CONFIG_CONSUL_TOKEN_FILE=/etc/certs/consul_token \
    GLUU_CONFIG_KUBERNETES_NAMESPACE=default \
    GLUU_CONFIG_KUBERNETES_CONFIGMAP=gluu \
    GLUU_CONFIG_KUBERNETES_USE_KUBE_CONFIG=false

# ==========
# Secret ENV
# ==========

ENV GLUU_SECRET_ADAPTER=vault \
    GLUU_SECRET_VAULT_SCHEME=http \
    GLUU_SECRET_VAULT_HOST=localhost \
    GLUU_SECRET_VAULT_PORT=8200 \
    GLUU_SECRET_VAULT_VERIFY=false \
    GLUU_SECRET_VAULT_ROLE_ID_FILE=/etc/certs/vault_role_id \
    GLUU_SECRET_VAULT_SECRET_ID_FILE=/etc/certs/vault_secret_id \
    GLUU_SECRET_VAULT_CERT_FILE=/etc/certs/vault_client.crt \
    GLUU_SECRET_VAULT_KEY_FILE=/etc/certs/vault_client.key \
    GLUU_SECRET_VAULT_CACERT_FILE=/etc/certs/vault_ca.crt \
    GLUU_SECRET_KUBERNETES_NAMESPACE=default \
    GLUU_SECRET_KUBERNETES_SECRET=gluu \
    GLUU_SECRET_KUBERNETES_USE_KUBE_CONFIG=false

# ===============
# Persistence ENV
# ===============

# available options: couchbase, ldap, hybrid
# only takes affect when GLUU_PERSISTENCE_TYPE is hybrid
# available options: default, user, cache, site, statistic
ENV GLUU_PERSISTENCE_TYPE=ldap \
    GLUU_PERSISTENCE_LDAP_MAPPING=default \
    GLUU_COUCHBASE_URL=localhost \
    GLUU_LDAP_URL=localhost:1636

# ===========
# Generic ENV
# ===========

ENV GLUU_MAX_RAM_PERCENTAGE=75.0 \
    GLUU_WAIT_MAX_TIME=300 \
    GLUU_WAIT_SLEEP_DURATION=10

# ==========
# misc stuff
# ==========

LABEL name="Radius" \
    maintainer="Gluu Inc. <support@gluu.org>" \
    vendor="Gluu Federation" \
    version="4.0.0" \
    release="dev" \
    summary="Gluu RADIUS" \
    description="RADIUS integration for Gluu Server"

RUN mkdir -p /etc/certs \
    /deploy \
    /opt/gluu/python/libs \
    /etc/gluu/conf/radius \
    /app

COPY static/gluu-radius-logging.xml /etc/gluu/conf/radius/
COPY templates /app/templates
COPY scripts /app/scripts
RUN chmod +x /app/scripts/entrypoint.sh

# # create non-root user
# RUN useradd -ms /bin/sh --uid 1000 jetty \
#     && usermod -a -G root jetty

# # adjust ownership
# RUN chown -R 1000:1000 /opt/gluu/jetty \
#     && chown -R 1000:1000 /deploy \
#     && chmod -R g+w /usr/lib/jvm/default-jvm/jre/lib/security/cacerts \
#     && chgrp -R 0 /opt/gluu/jetty && chmod -R g=u /opt/gluu/jetty \
#     && chgrp -R 0 /deploy && chmod -R g=u /deploy \
#     && chgrp -R 0 /etc/certs && chmod -R g=u /etc/certs \
#     && chgrp -R 0 /etc/gluu && chmod -R g=u /etc/gluu

# # run as non-root user
# USER 1000

ENTRYPOINT ["tini", "-g", "--"]
CMD ["/app/scripts/entrypoint.sh"]
