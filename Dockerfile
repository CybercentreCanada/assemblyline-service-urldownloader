ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch

ENV SERVICE_PATH=urldownloader.URLDownloader
ENV KANGOOROO_VERSION=v2.0.1.stable11
USER root

RUN apt update -y && \
    apt install -y wget default-jre unzip ffmpeg && \
    # Find out what is the latest version of the chrome-for-testing/chromedriver available
    VERS=$(wget -q -O - https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
    # Download + Install google-chrome with the version matching the latest chromedriver
    wget -O ./google-chrome-stable_amd64.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_$VERS-1_amd64.deb && \
    apt install -y ./google-chrome-stable_amd64.deb && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /opt/al_service/kangooroo && \
    # Download + unzip the latest chromedriver
    wget -O ./chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$VERS/linux64/chromedriver-linux64.zip && \
    unzip -j -d /opt/al_service/kangooroo ./chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm -f ./google-chrome-stable_current_amd64.deb ./chromedriver-linux64.zip && \
    # Download and install Kangooroo from Github
    wget -O ./KangoorooStandalone.zip https://github.com/CybercentreCanada/kangooroo/releases/download/$KANGOOROO_VERSION/KangoorooStandalone.zip && \
    unzip -j ./KangoorooStandalone.zip KangoorooStandalone/lib/* -d /opt/al_service/kangooroo/lib && \
    unzip -j ./KangoorooStandalone.zip KangoorooStandalone/bin/* -d /opt/al_service/kangooroo/bin && \
    rm -f ./KangoorooStandalone.zip


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
