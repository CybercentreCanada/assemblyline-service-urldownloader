ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch

ENV SERVICE_PATH=urldownloader.urldownloader.URLDownloader
ENV KANGOOROO_VERSION=v2.0.1.stable19
# latest version of chrome that we tested
ENV CHROME_VERSION=135.0.7049.114

# # Install apt dependencies
USER root
COPY pkglist.txt /tmp/setup/
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    $(grep -vE "^\s*(#|$)" /tmp/setup/pkglist.txt | tr "\n" " ") && \
    rm -rf /tmp/setup/pkglist.txt /var/lib/apt/lists/*



RUN wget -O ./google-chrome-stable_amd64.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_$CHROME_VERSION-1_amd64.deb && \
    apt update -y && \
    apt install -y ./google-chrome-stable_amd64.deb && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /opt/al_service/urldownloader/kangooroo && \
    wget -O ./chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chromedriver-linux64.zip && \
    unzip -j -d /opt/al_service/urldownloader/kangooroo ./chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm -f ./google-chrome-stable_current_amd64.deb ./chromedriver-linux64.zip && \

    # Download and install Kangooroo from Github
    wget -O ./KangoorooStandalone.zip https://github.com/CybercentreCanada/kangooroo/releases/download/$KANGOOROO_VERSION/KangoorooStandalone.zip && \
    unzip -j ./KangoorooStandalone.zip KangoorooStandalone/lib/* -d /opt/al_service/urldownloader/kangooroo/lib && \
    unzip -j ./KangoorooStandalone.zip KangoorooStandalone/bin/* -d /opt/al_service/urldownloader/kangooroo/bin && \
    rm -f ./KangoorooStandalone.zip





# Install python dependencies
USER assemblyline
COPY requirements.txt requirements.txt
RUN pip install \
    --no-cache-dir \
    --user \
    --requirement requirements.txt && \
    rm -rf ~/.cache/pip

# Copy service code
WORKDIR /opt/al_service
COPY . .

# Patch version in manifest
ARG version=1.0.0.dev1
USER root
RUN sed -i -e "s/\$SERVICE_TAG/$version/g" service_manifest.yml

# Switch to assemblyline user
USER assemblyline

# using dumb-init as entrypoint to remove zombie chrome processes
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python", "/etc/process_handler.py"]
