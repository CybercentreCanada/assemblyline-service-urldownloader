ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch

ENV SERVICE_PATH urldownloader.URLDownloader

USER root

RUN apt update -y && \
    apt install -y wget default-jre unzip && \
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt install -y ./google-chrome-stable_current_amd64.deb && \
    rm -rf /var/lib/apt/lists/* && \
    wget https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$(google-chrome --version | awk '{print $NF}')/linux64/chromedriver-linux64.zip && \
    unzip -j -d /opt/al_service ./chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm -f ./google-chrome-stable_current_amd64.deb ./chromedriver-linux64.zip

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
