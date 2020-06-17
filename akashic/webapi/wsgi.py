import logging
from akashic.webapi.webapi_factory import webapi_factory

def build_wsgi_prod(username, password, mongo_host, db_name):
    mongo_uri = "mongodb://{0}:{1}@{2}/" \
                 "{3}?authSource=admin&readPreference=primary&" \
                 "appname=MongoDB%20Compass&ssl=false" \
                 .format(username, password, mongo_host, db_name)

    print("MONGO_URL: " + mongo_uri)

    webapi = webapi_factory(mongo_uri)
    gunicorn_logger = logging.getLogger('gunicorn.error')
    webapi.logger.handlers = gunicorn_logger.handlers
    webapi.logger.setLevel(gunicorn_logger.level)

    return webapi


mongo_uri = "mongodb://admin:devdevdev@172.33.1.2:27017/" \
            "akashic?authSource=admin&readPreference=primary&" \
            "appname=MongoDB%20Compass&ssl=false"

webapi = webapi_factory(mongo_uri)
webapi.run(debug=True, host='172.33.1.3', port=5000)
