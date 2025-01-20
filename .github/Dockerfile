# FROM ubuntu:latest
# RUN apt-get update && apt-get install -y --no-install-recommends openssh-client git make python3-pip python3-dev docker.io && pip install uv --break-system-packages && apt-get clean && rm -rf /var/lib/apt/lists
# # Copy repository code into the image
# COPY ansible_collections/arista/avd/requirements-dev.txt /requirements-dev.txt
# # Install UV and Python virtual environments
# RUN uv python install 3.10 3.11 3.12 3.13 && \
#     uv venv --python 3.10 /UV3.10 && /UV3.10/bin/python -m ensurepip --upgrade && \
#     uv venv --python 3.11 /UV3.11 && /UV3.11/bin/python -m ensurepip --upgrade && \
#     uv venv --python 3.12 /UV3.12 && /UV3.12/bin/python -m ensurepip --upgrade && \
#     uv venv --python 3.13 /UV3.13 && /UV3.13/bin/python -m ensurepip --upgrade 
FROM ghcr.io/maheshgslab/avd-slim-test3:0.1
COPY ansible_collections/arista/avd/requirements-dev.txt /requirements-dev.txt
RUN uv python install 3.10 3.11 3.12 3.13 && \
    uv venv --python 3.10 /UV3.10 && /UV3.10/bin/python -m ensurepip --upgrade && \
    uv venv --python 3.11 /UV3.11 && /UV3.11/bin/python -m ensurepip --upgrade && \
    uv venv --python 3.12 /UV3.12 && /UV3.12/bin/python -m ensurepip --upgrade && \
    uv venv --python 3.13 /UV3.13 && /UV3.13/bin/python -m ensurepip --upgrade && \
    /UV3.10/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /requirements-dev.txt --upgrade && \
    /UV3.11/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /requirements-dev.txt --upgrade && \
    /UV3.12/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /requirements-dev.txt --upgrade && \
    /UV3.13/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /requirements-dev.txt --upgrade
# FROM ghcr.io/maheshgslab/avd-slim-test2:0.2
# RUN mkdir -p /avd && cp -rT ./ /avd
# WORKDIR /avd/python-avd
# RUN python3 -m pip install --break-system-packages build && \
#     python3 -m build --wheel --outdir /tmp/wheels
# RUN for VERSION in UV3.10 UV3.11 UV3.12 UV3.13; do \
#       /$VERSION/bin/python -m pip install --no-cache-dir /tmp/wheels/*.whl; \
#     done
