ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch

ENV SERVICE_PATH=urldownloader.URLDownloader
ENV KANGOOROO_VERSION=v2.0.1.stable14
USER root



RUN apt update -y && \
    apt install -y wget default-jre unzip ffmpeg


# Download + Install google-chrome with the version matching the latest chromedriver
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | tee /etc/apt/trusted.gpg.d/google.asc >/dev/null && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Download + unzip the latest chromedriver
RUN VERS=$(echo -n $(google-chrome --version | cut -c 15-)) && \
    wget -O ./chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$VERS/linux64/chromedriver-linux64.zip && \
    unzip ./chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm -f ./chromedriver-linux64.zip && \
    mv ./chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    # Cleanup
    rm -rf /tmp/*

# Download and install Kangooroo from Github
RUN mkdir /opt/al_service/kangooroo && \
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
