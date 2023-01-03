# vim: ai:sw=4:ts=4:sta:et:fo=croql
# pylint: disable=line-too-long
"""
Source: https://github.com/rednafi/flask-factory/blob/master/app/run.py
"""
# pylint: enable=line-too-long
import os

from yaas.entry_point import cloud_run

application = cloud_run.create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT")) if os.getenv("PORT") else 8080
    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    application.run(host="127.0.0.1", port=port, debug=True)
