ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch

ENV SERVICE_PATH urldownloader.URLDownloader

USER root

RUN apt update -y && \
    apt install -y wget default-jre unzip && \
    VERS=$(wget -q -O - https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) &&\
    wget -O ./google-chrome-stable_amd64.deb https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_$VERS-1_amd64.deb &&\
    apt install -y ./google-chrome-stable_amd64.deb && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir /opt/al_service/kangooroo &&\
    wget -O ./chromedriver-linux64.zip https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$VERS/linux64/chromedriver-linux64.zip && \
    unzip -j -d /opt/al_service/kangooroo ./chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm -f ./google-chrome-stable_current_amd64.deb ./chromedriver-linux64.zip &&\
    wget -O /opt/al_service/kangooroo/KangoorooStandalone.jar https://alpytest.blob.core.windows.net/pytest/KangoorooStandalone.jar

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
