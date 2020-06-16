from akashic.webapi.webapi_factory import webapi_factory

def build_wsgi(username, password, mongo_host, db_name):
    mongo_uri = "mongodb://{0}:{1}@{2}/" \
                 "{3}?authSource=admin&readPreference=primary&" \
                 "appname=MongoDB%20Compass&ssl=false" \
                 .format(username, password, mongo_host, db_name)

    print("MONGO_URL: " + mongo_uri)

    webapi = webapi_factory(mongo_uri)

    return webapi
