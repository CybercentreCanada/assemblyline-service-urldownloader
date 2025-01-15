[![Discord](https://img.shields.io/badge/chat-on%20discord-7289da.svg?sanitize=true)](https://discord.gg/GUAy9wErNu)
[![](https://img.shields.io/discord/908084610158714900)](https://discord.gg/GUAy9wErNu)
[![Static Badge](https://img.shields.io/badge/github-assemblyline-blue?logo=github)](https://github.com/CybercentreCanada/assemblyline)
[![Static Badge](https://img.shields.io/badge/github-assemblyline\_service\_urldownloader-blue?logo=github)](https://github.com/CybercentreCanada/assemblyline-service-urldownloader)
[![GitHub Issues or Pull Requests by label](https://img.shields.io/github/issues/CybercentreCanada/assemblyline/service-urldownloader)](https://github.com/CybercentreCanada/assemblyline/issues?q=is:issue+is:open+label:service-urldownloader)
[![License](https://img.shields.io/github/license/CybercentreCanada/assemblyline-service-urldownloader)](./LICENSE)
# URLdownloader Service

This Assemblyline service crawls URLs and records communications with the URL.

## Image variants and tags

Assemblyline services are built from the [Assemblyline service base image](https://hub.docker.com/r/cccs/assemblyline-v4-service-base),
which is based on Debian 11 with Python 3.11.

Assemblyline services use the following tag definitions:

| **Tag Type** | **Description**                                                                                  |      **Example Tag**       |
| :----------: | :----------------------------------------------------------------------------------------------- | :------------------------: |
|    latest    | The most recent build (can be unstable).                                                         |          `latest`          |
|  build_type  | The type of build used. `dev` is the latest unstable build. `stable` is the latest stable build. |     `stable` or `dev`      |
|    series    | Complete build details, including version and build type: `version.buildType`.                   | `4.5.stable`, `4.5.1.dev3` |

## Running this service

This is an Assemblyline service. It is designed to run as part of the Assemblyline framework.

If you would like to test this service locally, you can run the Docker image directly from the a shell:

    docker run \
        --name URLdownloader \
        --env SERVICE_API_HOST=http://`ip addr show docker0 | grep "inet " | awk '{print $2}' | cut -f1 -d"/"`:5003 \
        --network=host \
        cccs/assemblyline-service-urldownloader

To add this service to your Assemblyline deployment, follow this
[guide](https://cybercentrecanada.github.io/assemblyline4_docs/developer_manual/services/run_your_service/#add-the-container-to-your-deployment).

## Kubernetes VS Docker deployment
In Kubernetes, there is a chance that you do not need to configure the no_sandbox option. If you are executing URLDownloader in a docker-compose setup, and have problem with it always finishing with an error (TimeoutExpired), you can change the "no_sandbox" service variable from the default False to True. This option will be passed on to the google-chrome process and may resolve your issue.

Service variables are found under the Administration tab, in the Services item. More information on service management can be found in our documentation and more specifically [here](https://cybercentrecanada.github.io/assemblyline4_docs/administration/service_management/#service-variables) for service variables.

## How to configure a proxy
The URLDownloader service can be configured to use many proxies (or not) and allow the submitting user to pick from a choice. If you want to force a proxy, you can also have a single entry in the list of choices, and that will make it mandatory. URLDownloader does not rely on the system configuration because we have situations where we have multiple proxies and want to fetch content from different places. It could also happen that the proxies from which we want to fetch be different be different from the proxy used by the rest of the system.

You can configure the URLDownloader service by going to the list of services, and clicking on URLDownloader (or going to `/admin/services/URLDownloader` directly). You should find a tab named `PARAMETERS`. Two parameters are important, the first one being `proxies [json]` and the second being `proxy [list]`. It is easier to understand their relationship by starting with the `proxies [json]`, which should be found under the service variables toward the bottom of the page.

You can create new entries based on the following pattern:

![proxy-0](readme/proxy-0.png)

To edit a json in the web interface, you can hover on the json, a blue plus sign should appear toward the top:

![proxy-1](readme/proxy-1.png)

This will allow you to create a new key. By hovering on the new key, you should be able to edit it:

![proxy-2](readme/proxy-2.png)

You can then type in `{}` and click on the new dictionary button (bottom right in the next screenshot):

![proxy-3](readme/proxy-3.png)

You should now be able to add two new keys, for http and https.

![proxy-4](readme/proxy-4.png)

TIP: If you want to use the same proxy for all schemes (http/https), you can use a simple string:

![proxy-5](readme/proxy-5.png)

After configuring the service proxies, you can look toward the top, under User Specified Parameters, there should be `proxy [list]`.

![proxy-6](readme/proxy-6.png)

You will be able to add the name of the key you added (`my_new_proxy` in this example) so that the users can select it.
The entry with a star is going to be the default selection if a user does not configure it. You can delete all other entries from here to force a single one.

## Documentation

General Assemblyline documentation can be found at: https://cybercentrecanada.github.io/assemblyline4_docs/




# Service URLdownloader

Ce service Assemblyline explore les URL et enregistre les communications avec l'URL.

## Variantes et étiquettes d'image

Les services d'Assemblyline sont construits à partir de l'image de base [Assemblyline service](https://hub.docker.com/r/cccs/assemblyline-v4-service-base),
qui est basée sur Debian 11 avec Python 3.11.

Les services d'Assemblyline utilisent les définitions d'étiquettes suivantes:

| **Type d'étiquette** | **Description**                                                                                                |  **Exemple d'étiquette**   |
| :------------------: | :------------------------------------------------------------------------------------------------------------- | :------------------------: |
|   dernière version   | La version la plus récente (peut être instable).                                                               |          `latest`          |
|      build_type      | Type de construction utilisé. `dev` est la dernière version instable. `stable` est la dernière version stable. |     `stable` ou `dev`      |
|        série         | Détails de construction complets, comprenant la version et le type de build: `version.buildType`.              | `4.5.stable`, `4.5.1.dev3` |

## Exécution de ce service

Ce service est spécialement optimisé pour fonctionner dans le cadre d'un déploiement d'Assemblyline.

Si vous souhaitez tester ce service localement, vous pouvez exécuter l'image Docker directement à partir d'un terminal:

    docker run \
        --name URLdownloader \
        --env SERVICE_API_HOST=http://`ip addr show docker0 | grep "inet " | awk '{print $2}' | cut -f1 -d"/"`:5003 \
        --network=host \
        cccs/assemblyline-service-urldownloader

Pour ajouter ce service à votre déploiement d'Assemblyline, suivez ceci
[guide](https://cybercentrecanada.github.io/assemblyline4_docs/fr/developer_manual/services/run_your_service/#add-the-container-to-your-deployment).



## Déploiement Kubernetes VS Docker
Dans Kubernetes, il est possible que vous n'ayez pas besoin de configurer l'option no_sandbox. Si vous exécutez URLDownloader dans une configuration Docker-compose et que vous rencontrez des problèmes avec le fait qu'il se termine toujours par une erreur (TimeoutExpired), vous pouvez modifier la variable de service "no_sandbox" de False par défaut à True. Cette option sera transmise au processus Google-Chrome et pourra résoudre votre problème.

Service variables are found under the Administration tab, in the Services item. More information on service management can be found in our documentation and more specifically [here](https://cybercentrecanada.github.io/assemblyline4_docs/administration/service_management/#service-variables) for service variables.

## How to configure a proxy
TLe service URLDownloader peut être configuré pour utiliser de nombreux proxys (ou non) et permettre à l'utilisateur soumettant de choisir parmi un choix. Si vous souhaitez forcer un proxy, vous pouvez aussi avoir une seule entrée dans la liste de choix, et cela la rendra obligatoire. URLDownloader ne s'appuie pas sur la configuration du système car nous avons des situations dans lesquelles nous avons plusieurs proxys et souhaitons récupérer du contenu à différents endroits. Il peut également arriver que les proxys à partir desquels nous souhaitons récupérer soient différents du proxy utilisé par le reste du système.

Vous pouvez configurer le service URLDownloader en accédant à la liste des services et en cliquant sur URLDownloader (ou en allant directement sur `/admin/services/URLDownloader`).

Vous devriez trouver un onglet nommé `PARAMETERS`. Deux paramètres sont importants, le premier étant `proxies [json]` et le second étant  `proxy [list]`. Il est plus facile de comprendre leur relation en commençant par les `proxies [json]`, qui doivent se trouver sous les variables de service en bas de la page.


Vous pouvez créer de nouvelles entrées basées sur le modèle suivant :

![proxy-0](readme/proxy-0.png)

Pour modifier un json dans l'interface web, vous pouvez survoler le json, un signe plus bleu doit apparaître vers le haut:

![proxy-1](readme/proxy-1.png)

Cela vous permettra de créer une nouvelle clé. En survolant la nouvelle clé, vous devriez pouvoir la modifier:

![proxy-2](readme/proxy-2.png)

Vous pouvez ensuite taper `{}` et cliquer sur le bouton nouveau dictionnaire (en bas à droite dans la capture d'écran suivante) :

![proxy-3](readme/proxy-3.png)

Vous devriez maintenant pouvoir ajouter deux nouvelles clés, pour http et https.

![proxy-4](readme/proxy-4.png)

CONSEIL : Si vous souhaitez utiliser le même proxy pour tous les schémas (http/https), vous pouvez utiliser une simple chaîne :

![proxy-5](readme/proxy-5.png)

Après avoir configuré les proxys de service, vous pouvez regarder vers le haut, sous 'User Specified Parameters', il devrait y avoir `proxy [list]`.


![proxy-6](readme/proxy-6.png)

Vous pourrez ajouter le nom de la clé que vous avez ajoutée (`my_new_proxy` dans cet exemple) afin que les utilisateurs puissent la sélectionner.

L'entrée avec une étoile sera la sélection par défaut si un utilisateur ne la configure pas. Vous pouvez supprimer toutes les autres entrées à partir d’ici pour en forcer une seule.


## Documentation

La documentation générale sur Assemblyline peut être consultée à l'adresse suivante: https://cybercentrecanada.github.io/assemblyline4_docs/
