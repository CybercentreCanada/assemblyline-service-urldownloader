[![Discord](https://img.shields.io/badge/chat-on%20discord-7289da.svg?sanitize=true)](https://discord.gg/GUAy9wErNu)
[![](https://img.shields.io/discord/908084610158714900)](https://discord.gg/GUAy9wErNu)
[![Static Badge](https://img.shields.io/badge/github-assemblyline-blue?logo=github)](https://github.com/CybercentreCanada/assemblyline)
[![Static Badge](https://img.shields.io/badge/github-assemblyline_service_urldownloader-blue?logo=github)](https://github.com/CybercentreCanada/assemblyline-service-urldownloader)
[![GitHub Issues or Pull Requests by label](https://img.shields.io/github/issues/CybercentreCanada/assemblyline/service-urldownloader)](https://github.com/CybercentreCanada/assemblyline/issues?q=is:issue+is:open+label:service-urldownloader)
[![License](https://img.shields.io/github/license/CybercentreCanada/assemblyline-service-urldownloader)](./LICENSE)

# URLDownloader Service

This service downloads potentially malicious URLs. It uses the Java program [Kangooroo](https://github.com/CybercentreCanada/kangooroo).

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
        --name URLDownloader \
        --env SERVICE_API_HOST=http://`ip addr show docker0 | grep "inet " | awk '{print $2}' | cut -f1 -d"/"`:5003 \
        --network=host \
        cccs/assemblyline-service-urldownloader

To add this service to your Assemblyline deployment, follow this
[guide](https://cybercentrecanada.github.io/assemblyline4_docs/developer_manual/services/run_your_service/#add-the-container-to-your-deployment).

## URLDownloader service configuration

Administrators can find the configuration page for URLDownloader by going to the **Administration > Services** page, and click on **URLDownloader** (or by going to `/admin/services/URLDownloader` directly).
_Service Variables_ and _User Specified Parameters_ can be found in the **Parameters** tab.

More information on service management can be found in our documentation and more specifically [here](https://cybercentrecanada.github.io/assemblyline4_docs/administration/service_management/#service-variables) for service variables.

## How to configure a proxy

The URLDownloader service can be configured to use zero to many proxies, and it allows users to pick from a list of proxies for their URL submissions.
An administrator can force a proxy on all submissions by configuring a single entry in the proxy list to make it mandatory.
URLDownloader does not automatically detect proxies based on system configurations.
You can configure proxy settings from the URLDownloader configuration page in the **Service Variables** section using `proxies [json]` and `proxy [list]`.

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

## Modifying browser settings

You can configure the following browser settings in URLDownloader:

- User agent(`user_agent`): This is the value of `User-Agent` in request headers.
- Window size(`window_size`): The screen resolution of the browser.
- Request headers (`headers`/`request_headers`): Request headers used to fetch URLs.

Administrators can set the default values for these settings from the URLDownloader configuration page in the **Service Variables** section.
These settings will be used by every single submissions sent to URLDownloader.

Here is an example of `default_browser_settings [json]` service variable:

```
# iPhone 11 Pro configuration:
{
    "window_size": "375x812",
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "request_headers":
    {
        "Sec-CH-UA-Mobile": "?1"
    }
}
```

Users can also modify these settings per URL submission by submitting an Assemblyline URI file.
Here is an example file **Assemblyline URI file 1**:

```
# Assemblyline URI file
uri: https://sample_webpage.com/

browser_settings:
    window_size: 1280x720
    user_agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36

# request headers
headers:
    test-platform: Windows
```

The values set by the URI file will override the values set by `default_browser_settings`.
If `headers` value is set in the URI file, its value overwrites the service parameter values set in `default_browser_settings.request_headers`.

Using the above `default_browser_settings` and _Assemblyline URI file 1_ as an example, these will be the settings used by URLDownloader:

```
uri: https://sample_webpage.com/

# Using settings from Assemblyline URI file 1
window_size: 1280x720
user_agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36
request_headers:
    test-platform: Windows
```

Users have the option to change only the settings that are relevant to them and URLDownloader will use the values in `default_browser_settings` for the rest.
For example, given this **Assemblyline URI file 2**:

```
# Assemblyline URI file
uri: https://sample_webpage.com/

browser_settings:
    window_size: 2000x2000
```

Combining _Assemblyline URI file 2_ with the `default_browser_settings` stated above, these will be the settings used by URLDownloader:

```
uri: https://sample_webpage.com/

window_size: 2000x2000 # from URI file
user_agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1 # from default settings
request_headers: # from default settings
    Sec-CH-UA-Mobile: ?1
```

Users can check the settings used by each submission by looking at the file `Service Results > URLDownloader > Supplementary files > results.json (kangooroo Result Output)`.

#### Notes:

- If `headers` is not specified or is empty in the Assemblyline URI file, then the `default_browser_settings.request_headers` value will be used.
- If `headers` is defined in the Assemblyline URI file, only the values in `headers` will be used for request headers.
- Everything defined in the URI file will be prioritized over values defined in `default_browser_settings`.
- Any extra fields defined in the Assemblyline URI file will be ignored.
- If both `browser_settings.user_agent` and "User-Agent" field is defined in `headers`. Only the value of "User-Agent" in `headers` will be used in request headers.

## Documentation

General Assemblyline documentation can be found at: https://cybercentrecanada.github.io/assemblyline4_docs/

# Service URLDownloader

Ce service télécharge des URL potentiellement malveillantes.

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
        --name URLDownloader \
        --env SERVICE_API_HOST=http://`ip addr show docker0 | grep "inet " | awk '{print $2}' | cut -f1 -d"/"`:5003 \
        --network=host \
        cccs/assemblyline-service-urldownloader

Pour ajouter ce service à votre déploiement d'Assemblyline, suivez ceci
[guide](https://cybercentrecanada.github.io/assemblyline4_docs/fr/developer_manual/services/run_your_service/#add-the-container-to-your-deployment).

## Configuration du service URLDownloader

Les administrateurs peuvent trouver la page de configuration d'URLDownloader en allant sur la page **Administration > Services**, et en cliquant sur **URLDownloader** (ou en allant directement sur `/admin/services/URLDownloader`).
Les _variables de service_ et les _paramètres spécifiés par l'utilisateur_ se trouvent dans l'onglet **Paramètres**.

## Comment configurer un proxy

Le service URLDownloader peut être configuré pour utiliser de zéro à plusieurs proxys, et il permet aux utilisateurs de choisir parmi une liste de proxys pour leurs soumissions d'URL.
Un administrateur peut forcer l'utilisation d'un proxy pour toutes les soumissions en configurant une seule entrée dans la liste des proxys pour la rendre obligatoire.
URLDownloader ne détecte pas automatiquement les serveurs mandataires en fonction de la configuration du système.
Vous pouvez configurer les paramètres du proxy depuis la page de configuration d'URLDownloader dans la section **Variables de service** en utilisant `proxies [json]` et `proxy [list]`.

Vous pouvez créer de nouvelles entrées sur la base du modèle suivant :

![proxy-0](readme/proxy-0.png)

Pour éditer un json dans l'interface web, vous pouvez survoler le json, un signe plus bleu devrait apparaître vers le haut :

![proxy-1](readme/proxy-1.png)

Cela vous permettra de créer une nouvelle clé. En survolant la nouvelle clé, vous devriez pouvoir la modifier :

![proxy-2](readme/proxy-2.png)

Vous pouvez alors taper `{}` et cliquer sur le bouton nouveau dictionnaire (en bas à droite dans la capture d'écran suivante) :

![proxy-3](readme/proxy-3.png)

Vous devriez maintenant être en mesure d'ajouter deux nouvelles clés, pour http et https.

![proxy-4](readme/proxy-4.png)

ASTUCE : Si vous souhaitez utiliser le même proxy pour tous les schémas (http/https), vous pouvez utiliser une simple chaîne de caractères :

![proxy-5](readme/proxy-5.png)

Après avoir configuré les proxys de service, vous pouvez regarder vers le haut, sous Paramètres spécifiés par l'utilisateur, il devrait y avoir `proxy [list]`.

![proxy-6](readme/proxy-6.png)

Vous pourrez ajouter le nom de la clé que vous avez ajoutée (`my_new_proxy` dans cet exemple) afin que les utilisateurs puissent la sélectionner.
L'entrée avec une étoile sera la sélection par défaut si l'utilisateur ne la configure pas. Vous pouvez supprimer toutes les autres entrées pour en forcer une seule.

## Modifier les paramètres du navigateur

Vous pouvez configurer les paramètres suivants du navigateur dans URLDownloader :

- Agent utilisateur (`user_agent`): Agent utilisateur (`user_agent`) : C'est la valeur de `User-Agent` dans les en-têtes de la requête.
- Taille de la fenêtre (`window_size`): La résolution d'écran du navigateur.
- En-têtes de la demande (`headers`/`request_headers`): En-têtes de requête utilisés pour récupérer les URL.

Les administrateurs peuvent définir les valeurs par défaut de ces paramètres à partir de la page de configuration d'URLDownloader, dans la section **Variables de service**.
Ces paramètres seront utilisés pour chaque soumission envoyée à URLDownloader.

Voici un exemple de variable de service `default_browser_settings [json]` :

```
# iPhone 11 Pro configuration:
{
    "window_size": "375x812",
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "request_headers":
    {
        "Sec-CH-UA-Mobile": "?1"
    }
}
```

Les utilisateurs peuvent également modifier ces paramètres par soumission d'URL en soumettant un fichier URI Assemblyline.
Voici un exemple de fichier **Fichier URI Assemblyline 1** :

```
# Assemblyline URI file
uri: https://sample_webpage.com/

browser_settings:
    window_size: 1280x720
    user_agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36

# request headers
headers:
    test-platform: Windows
```

Les valeurs définies par le fichier URI remplaceront les valeurs définies par `default_browser_settings`.
Si la valeur `headers` est définie dans le fichier URI, sa valeur écrase les valeurs des paramètres de service définies dans `default_browser_settings.request_headers`.

En utilisant les `default_browser_settings` ci-dessus et _Assemblyline URI file 1_ comme exemple, ce seront les paramètres utilisés par URLDownloader :

```
uri: https://sample_webpage.com/

# Utilisation des paramètres du fichier URI Assemblyline 1
window_size: 1280x720
user_agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36
request_headers:
    test-platform: Windows
```

Users have the option to change only the settings that are relevant to them and URLDownloader will use the values in `default_browser_settings` for the rest.
For example, given this **Assemblyline URI file 2**:

```
# Assemblyline URI file
uri: https://sample_webpage.com/

browser_settings:
    window_size: 2000x2000
```

En combinant _Assemblyline URI file 2_ avec les `default_browser_settings` mentionnés ci-dessus, ces paramètres seront utilisés par URLDownloader :

```
uri: https://sample_webpage.com/

window_size: 2000x2000 # from URI file
user_agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1 # from default settings
request_headers: # from default settings
    Sec-CH-UA-Mobile: ?1
```

Les utilisateurs peuvent vérifier les paramètres utilisés par chaque soumission en consultant le fichier `Résultats du service > URLDownloader > Fichiers supplémentaires > results.json (kangooroo Result Output)`.

#### Notes:

- Si `headers` n'est pas spécifié ou est vide dans le fichier URI de l'Assemblyline, alors la valeur `default_browser_settings.request_headers` sera utilisée.
- Si `headers` est défini dans le fichier URI de l'Assemblyline, seules les valeurs de `headers` seront utilisées pour les en-têtes de la requête.
- Tout ce qui est défini dans le fichier URI sera prioritaire sur les valeurs définies dans `default_browser_settings`.
- Tout champ supplémentaire défini dans le fichier URI de la ligne d'assemblage sera ignoré.
- Si le champ `browser_settings.user_agent` et le champ « User-Agent » sont tous deux définis dans `headers`. Seule la valeur de « User-Agent » dans `headers` sera utilisée dans les en-têtes de la requête.

## Documentation

La documentation générale sur Assemblyline peut être consultée à l'adresse suivante: https://cybercentrecanada.github.io/assemblyline4_docs/
