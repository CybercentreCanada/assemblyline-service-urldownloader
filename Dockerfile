ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch

ENV SERVICE_PATH urldownloader.urldownloader.URLDownloader

USER root

# Install Chrome for headless rendering of HTML documents
RUN apt update -y && apt install wget && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && rm -f ./google-chrome-stable_current_amd64.deb

# Switch to assemblyline user
USER assemblyline

# Copy service code
WORKDIR /opt/al_service
COPY . .

# Install python dependencies
RUN pip install --no-cache-dir --user --requirement requirements.txt && rm -rf ~/.cache/pip

# Patch version in manifest
ARG version=4.0.0.dev1
USER root
RUN sed -i -e "s/\$SERVICE_TAG/$version/g" service_manifest.yml

# Switch to assemblyline user
USER assemblyline
