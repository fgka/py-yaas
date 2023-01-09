ARG BASE_IMAGE=yaas_base:latest
FROM ${BASE_IMAGE}

ARG PIP_INSTALL_ARG=./py_yaas_playground-1.0-py2.py3-none-any.whl

COPY dist/*.whl ./

RUN python3 -m pip install ${PIP_INSTALL_ARG}

ENV FLASK_APP yaas.entry_point.flask_gunicorn:APPLICATION

CMD gunicorn --bind ":${PORT}" --workers 1 --threads 8 --timeout 0 ${FLASK_APP}
