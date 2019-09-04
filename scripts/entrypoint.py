import os
# import re

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
            "mapping": "",
        },
        "user": {
            "bucket": "gluu_user",
            "mapping": "people, groups, authorizations"
        },
        "cache": {
            "bucket": "gluu_cache",
            "mapping": "cache",
        },
        "site": {
            "bucket": "gluu_site",
            "mapping": "cache-refresh",
        },
        "authorization": {
            "bucket": "gluu_authorization",
            "mapping": "authorizations",
        },
        "token": {
            "bucket": "gluu_token",
            "mapping": "tokens",
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

        if not mapping["mapping"]:
            continue

        couchbase_mappings.append("bucket.{0}.mapping: {1}".format(
            mapping["bucket"], mapping["mapping"],
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
        mapping["mapping"] for name, mapping in _couchbase_mappings.iteritems()
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


if __name__ == "__main__":
    main()
