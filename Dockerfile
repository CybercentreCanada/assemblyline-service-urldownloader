ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch

ENV SERVICE_PATH=urldownloader.URLDownloader
ENV KANGOOROO_VERSION=v2.0.1.stable16
USER root

RUN apt update -y && \
    apt install -y wget default-jre unzip ffmpeg dumb-init


# Find out what is the latest version of the chromedriver & chome from chrome-for-testing available
RUN VERS=$(wget -q -O - https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
    # Download + Install google-chrome with the version matching the latest chromedriver
    mkdir -p /opt/google /opt/al_service/kangooroo && \
    wget -O ./chrome-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$VERS/linux64/chrome-linux64.zip && \
    unzip ./chrome-linux64.zip && \
    while read pkg; do apt-get satisfy -y --no-install-recommends "$pkg"; done < chrome-linux64/deb.deps &&\
    mv chrome-linux64 /opt/google/chrome && \
    ln -s /opt/google/chrome/chrome /usr/bin/google-chrome && \

    # Download + unzip the latest chromedriver
    wget -O ./chromedriver-linux64.zip https://storage.googleapis.com/chrome-for-testing-public/$VERS/linux64/chromedriver-linux64.zip && \
    unzip -j -d /opt/al_service/kangooroo ./chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm -f ./chrome-linux64.zip ./chromedriver-linux64.zip && \
    # Cleanup
    rm -rf /tmp/* && \

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

# using dumb-init as entrypoint to remove zombie chrome processes
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["python", "/etc/process_handler.py"]
