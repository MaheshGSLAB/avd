FROM ubuntu:latest
RUN apt-get update && apt-get install -y --no-install-recommends openssh-client git make python3-pip python3-dev docker.io && pip install uv --break-system-packages && apt-get clean && rm -rf /var/lib/apt/lists
# Copy repository code into the image
COPY ansible_collections/arista/avd/requirements-dev.txt /requirements-dev.txt
# Install UV and Python virtual environments
RUN uv python install 3.10 3.11 3.12 3.13 && \
    uv venv --python 3.10 /UV3.10 && /UV3.10/bin/python -m ensurepip --upgrade && \
    uv venv --python 3.11 /UV3.11 && /UV3.11/bin/python -m ensurepip --upgrade && \
    uv venv --python 3.12 /UV3.12 && /UV3.12/bin/python -m ensurepip --upgrade && \
    uv venv --python 3.13 /UV3.13 && /UV3.13/bin/python -m ensurepip --upgrade && \
    /UV3.10/bin/python -m pip install -r /requirements-dev.txt --upgrade && \
    /UV3.11/bin/python -m pip install -r /requirements-dev.txt --upgrade && \
    /UV3.12/bin/python -m pip install -r /requirements-dev.txt --upgrade && \
    /UV3.13/bin/python -m pip install -r /requirements-dev.txt --upgrade
