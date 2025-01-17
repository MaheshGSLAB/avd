FROM ghcr.io/maheshgslab/avd-slim-test:0.1


# Copy the repository content into the container
COPY . /avd

RUN /UV3.10/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /avd/ansible_collections/arista/avd/requirements-dev.txt
RUN /UV3.11/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /avd/ansible_collections/arista/avd/requirements-dev.txt
RUN /UV3.12/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /avd/ansible_collections/arista/avd/requirements-dev.txt
RUN /UV3.13/bin/python -m pip install mock pytest pytest-mock pytest-xdist pyyaml "ansible-core<2.19.0" -r /avd/ansible_collections/arista/avd/requirements-dev.txt

