# URLDownloader Service
Assemblyline service that downloads seemingly malicious URLs using MAS' Kangooroo utility

# Kubernetes VS Docker deployment
In Kubernetes, there is a chance that you do not need to configure the no_sandbox option. If you are executing URLDownloader in a docker-compose setup, and have problem with it always finishing with an error, you can try to enable the "no_sandbox" option. This option will be passed on to the google-chrome process and may resolve your issue.
