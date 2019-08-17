import os
import re

from pygluu.containerlib import get_manager

GLUU_LDAP_URL = os.environ.get("GLUU_LDAP_URL", "localhost:1636")
GLUU_COUCHBASE_URL = os.environ.get("GLUU_COUCHBASE_URL", "localhost")
GLUU_PERSISTENCE_TYPE = os.environ.get("GLUU_PERSISTENCE_TYPE", "ldap")
GLUU_PERSISTENCE_LDAP_MAPPING = os.environ.get("GLUU_PERSISTENCE_LDAP_MAPPING", "default")

manager = get_manager()


def render_salt():
    encode_salt = manager.secret.get("encoded_salt")

    with open("/app/templates/salt.tmpl") as fr:
        txt = fr.read()
        with open("/etc/gluu/conf/salt", "w") as fw:
            rendered_txt = txt % {"encode_salt": encode_salt}
            fw.write(rendered_txt)


def render_ldap_properties():
    with open("/app/templates/gluu-ldap.properties.tmpl") as fr:
        txt = fr.read()

        ldap_hostname, ldaps_port = GLUU_LDAP_URL.split(":")

        with open("/etc/gluu/conf/gluu-ldap.properties", "w") as fw:
            rendered_txt = txt % {
                "ldap_binddn": manager.config.get("ldap_binddn"),
                "encoded_ox_ldap_pw": manager.secret.get("encoded_ox_ldap_pw"),
                "ldap_hostname": ldap_hostname,
                "ldaps_port": ldaps_port,
                "ldapTrustStoreFn": manager.config.get("ldapTrustStoreFn"),
                "encoded_ldapTrustStorePass": manager.secret.get("encoded_ldapTrustStorePass"),
            }
            fw.write(rendered_txt)


def get_couchbase_mappings():
    mappings = {
        "default": {
            "bucket": "gluu",
            "alias": "",
        },
        "user": {
            "bucket": "gluu_user",
            "alias": "people, groups"
        },
        "cache": {
            "bucket": "gluu_cache",
            "alias": "cache",
        },
        "statistic": {
            "bucket": "gluu_statistic",
            "alias": "statistic",
        },
        "site": {
            "bucket": "gluu_site",
            "alias": "cache-refresh",
        },
        "authorization": {
            "bucket": "gluu_authorization",
            "alias": "authorizations",
        },
        "tokens": {
            "bucket": "gluu_tokens",
            "alias": "tokens",
        },
        "clients": {
            "bucket": "gluu_clients",
            "alias": "clients",
        },
    }

    if GLUU_PERSISTENCE_TYPE == "hybrid":
        mappings = {
            name: mapping for name, mapping in mappings.iteritems()
            if name != GLUU_PERSISTENCE_LDAP_MAPPING
        }

    return mappings


def render_couchbase_properties():
    _couchbase_mappings = get_couchbase_mappings()
    couchbase_buckets = []
    couchbase_mappings = []

    for _, mapping in _couchbase_mappings.iteritems():
        couchbase_buckets.append(mapping["bucket"])

        if not mapping["alias"]:
            continue

        couchbase_mappings.append("bucket.{0}.mapping: {1}".format(
            mapping["bucket"], mapping["alias"],
        ))

    # always have `gluu` as default bucket
    if "gluu" not in couchbase_buckets:
        couchbase_buckets.insert(0, "gluu")

    with open("/app/templates/gluu-couchbase.properties.tmpl") as fr:
        txt = fr.read()

        ldap_hostname, ldaps_port = GLUU_LDAP_URL.split(":")

        with open("/etc/gluu/conf/gluu-couchbase.properties", "w") as fw:
            rendered_txt = txt % {
                "hostname": GLUU_COUCHBASE_URL,
                "couchbase_server_user": manager.config.get("couchbase_server_user"),
                "encoded_couchbase_server_pw": manager.secret.get("encoded_couchbase_server_pw"),
                "couchbase_buckets": ", ".join(couchbase_buckets),
                "default_bucket": "gluu",
                "couchbase_mappings": "\n".join(couchbase_mappings),
                "encryption_method": "SSHA-256",
                "ssl_enabled": "true",
                "couchbaseTrustStoreFn": manager.config.get("couchbaseTrustStoreFn"),
                "encoded_couchbaseTrustStorePass": manager.secret.get("encoded_couchbaseTrustStorePass"),
            }
            fw.write(rendered_txt)


def render_hybrid_properties():
    _couchbase_mappings = get_couchbase_mappings()

    ldap_mapping = GLUU_PERSISTENCE_LDAP_MAPPING

    if GLUU_PERSISTENCE_LDAP_MAPPING == "default":
        default_storage = "ldap"
    else:
        default_storage = "couchbase"

    couchbase_mappings = [
        mapping["alias"] for name, mapping in _couchbase_mappings.iteritems()
        if name != ldap_mapping
    ]

    out = "\n".join([
        "storages: ldap, couchbase",
        "storage.default: {}".format(default_storage),
        "storage.ldap.mapping: {}".format(ldap_mapping),
        "storage.couchbase.mapping: {}".format(
            ", ".join(filter(None, couchbase_mappings))
        ),
    ]).replace("user", "people, group")

    with open("/etc/gluu/conf/gluu-hybrid.properties", "w") as fw:
        fw.write(out)


def render_gluu_properties():
    with open("/app/templates/gluu.properties.tmpl") as fr:
        txt = fr.read()

        ldap_hostname, ldaps_port = GLUU_LDAP_URL.split(":")

        with open("/etc/gluu/conf/gluu.properties", "w") as fw:
            rendered_txt = txt % {
                "gluuOptPythonFolder": "/opt/gluu/python",
                "certFolder": "/etc/certs",
                "persistence_type": GLUU_PERSISTENCE_TYPE,
            }
            fw.write(rendered_txt)


def modify_jetty_xml():
    fn = "/opt/jetty/etc/jetty.xml"
    with open(fn) as f:
        txt = f.read()

    # disable contexts
    updates = re.sub(
        r'<New id="DefaultHandler" class="org.eclipse.jetty.server.handler.DefaultHandler"/>',
        r'<New id="DefaultHandler" class="org.eclipse.jetty.server.handler.DefaultHandler">\n\t\t\t\t <Set name="showContexts">false</Set>\n\t\t\t </New>',
        txt,
        flags=re.DOTALL | re.M,
    )

    # disable Jetty version info
    updates = re.sub(
        r'(<Set name="sendServerVersion"><Property name="jetty.httpConfig.sendServerVersion" deprecated="jetty.send.server.version" default=")true(" /></Set>)',
        r'\1false\2',
        updates,
        flags=re.DOTALL | re.M,
    )

    with open(fn, "w") as f:
        f.write(updates)


def modify_webdefault_xml():
    fn = "/opt/jetty/etc/webdefault.xml"
    with open(fn) as f:
        txt = f.read()

    # disable dirAllowed
    updates = re.sub(
        r'(<param-name>dirAllowed</param-name>)(\s*)(<param-value>)true(</param-value>)',
        r'\1\2\3false\4',
        txt,
        flags=re.DOTALL | re.M,
    )

    with open(fn, "w") as f:
        f.write(updates)


def render_radius_properties():
    with open("/app/templates/gluu-radius.properties.tmpl") as fr:
        txt = fr.read()

        with open("/etc/gluu/conf/radius/gluu-radius.properties", "w") as fw:
            rendered_txt = txt % {
                "radius_jwt_pass": manager.secret.get("radius_jwt_pass"),
                "radius_jwt_keyId": manager.config.get("radius_jwt_keyId"),
            }
            fw.write(rendered_txt)


def main():
    render_salt()
    render_gluu_properties()
    render_radius_properties()

    if GLUU_PERSISTENCE_TYPE in ("ldap", "hybrid"):
        render_ldap_properties()
        manager.secret.to_file(
            "ldap_pkcs12_base64",
            manager.config.get("ldapTrustStoreFn"),
            decode=True,
            binary_mode=True,
        )

    if GLUU_PERSISTENCE_TYPE in ("couchbase", "hybrid"):
        render_couchbase_properties()
        manager.secret.to_file(
            "couchbase_pkcs12_base64",
            manager.config.get("couchbaseTrustStoreFn"),
            decode=True,
            binary_mode=True,
        )

    if GLUU_PERSISTENCE_TYPE == "hybrid":
        render_hybrid_properties()

    manager.secret.to_file("ssl_cert", "/etc/certs/gluu_https.crt")
    manager.secret.to_file("ssl_key", "/etc/certs/gluu_https.key")
    manager.secret.to_file("radius_jks_base64", "/etc/certs/gluu-radius.jks",
                           decode=True, binary_mode=True)

    modify_jetty_xml()
    modify_webdefault_xml()


if __name__ == "__main__":
    main()
