import os

from pygluu.containerlib import get_manager
from pygluu.containerlib.persistence import render_salt
from pygluu.containerlib.persistence import render_gluu_properties
from pygluu.containerlib.persistence import render_ldap_properties
from pygluu.containerlib.persistence import render_couchbase_properties
from pygluu.containerlib.persistence import render_hybrid_properties
from pygluu.containerlib.persistence import sync_ldap_truststore
from pygluu.containerlib.persistence import sync_couchbase_truststore
# from pygluu.containerlib.persistence import sync_couchbase_cert
from pygluu.containerlib.utils import get_server_certificate
from pygluu.containerlib.utils import cert_to_truststore


def render_radius_properties(manager, src, dest):
    with open(src) as f:
        txt = f.read()

    with open(dest, "w") as f:
        rendered_txt = txt % {
            "radius_jwt_pass": manager.secret.get("radius_jwt_pass"),
            "radius_jwt_keyId": manager.config.get("radius_jwt_keyId"),
        }
        f.write(rendered_txt)


def main():
    manager = get_manager()
    persistence_type = os.environ.get("GLUU_PERSISTENCE_TYPE", "ldap")

    render_salt(manager, "/app/templates/salt.tmpl", "/etc/gluu/conf/salt")
    render_gluu_properties("/app/templates/gluu.properties.tmpl", "/etc/gluu/conf/gluu.properties")
    render_radius_properties(
        manager, "/app/templates/gluu-radius.properties.tmpl", "/etc/gluu/conf/radius/gluu-radius.properties")

    if persistence_type in ("ldap", "hybrid"):
        render_ldap_properties(
            manager,
            "/app/templates/gluu-ldap.properties.tmpl",
            "/etc/gluu/conf/gluu-ldap.properties",
        )
        sync_ldap_truststore(manager)

    if persistence_type in ("couchbase", "hybrid"):
        render_couchbase_properties(
            manager,
            "/app/templates/gluu-couchbase.properties.tmpl",
            "/etc/gluu/conf/gluu-couchbase.properties",
        )
        # sync_couchbase_cert(manager)
        sync_couchbase_truststore(manager)

    if persistence_type == "hybrid":
        render_hybrid_properties("/etc/gluu/conf/gluu-hybrid.properties")

    get_server_certificate(manager.config.get("hostname"), 443, "/etc/certs/gluu_https.crt")
    cert_to_truststore(
        "gluu_https",
        "/etc/certs/gluu_https.crt",
        "/usr/lib/jvm/default-jvm/jre/lib/security/cacerts",
        "changeit",
    )
    manager.secret.to_file("radius_jks_base64", "/etc/certs/gluu-radius.jks",
                           decode=True, binary_mode=True)


if __name__ == "__main__":
    main()
