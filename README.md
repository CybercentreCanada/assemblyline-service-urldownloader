# URLDownloader Service
Assemblyline service that downloads seemingly malicious URLs using MAS' Kangooroo utility

# Kubernetes VS Docker deployment
In Kubernetes, there is a chance that you do not need to configure the no_sandbox option. If you are executing URLDownloader in a docker-compose setup, and have problem with it always finishing with an error (TimeoutExpired), you can change the "no_sandbox" service variable from the default False to True. This option will be passed on to the google-chrome process and may resolve your issue.

Service variables are found under the Administration tab, in the Services item. More information on service management can be found in our documentation and more specifically [here](https://cybercentrecanada.github.io/assemblyline4_docs/administration/service_management/#service-variables) for service variables.
