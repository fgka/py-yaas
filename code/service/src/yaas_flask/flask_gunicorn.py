# vim: ai:sw=4:ts=4:sta:et:fo=croql
"""
Source: https://github.com/rednafi/flask-factory/blob/master/app/run.py
"""
import os

import flask


def run(application: flask.Flask) -> None:
    port = int(os.getenv("PORT")) if os.getenv("PORT") else 8080
    application.run(host="127.0.0.1", port=port, debug=True)
