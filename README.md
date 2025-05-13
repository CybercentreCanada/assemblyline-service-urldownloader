# URLDownloader Service

Assemblyline service that downloads seemingly malicious URLs using MAS' Kangooroo utility

## URLDownloader Service Configuration

Administrators can find the configuration page for URLDownloader by going to the **Adiministration > Services** page, and click on **URLDownloader** (or by going to `/admin/services/URLDownloader` directly).
_Service Variables_ and _User Specified Parameters_ can be found in the **Parameters** tab.

More information on service management can be found in our documentation and more specifically [here](https://cybercentrecanada.github.io/assemblyline4_docs/administration/service_management/#service-variables) for service variables.

<!-- # Kubernetes VS Docker deployment

In Kubernetes, there is a chance that you do not need to configure the no_sandbox option. If you are executing URLDownloader in a docker-compose setup, and have problem with it always finishing with an error (TimeoutExpired), you can change the "no_sandbox" service variable from the default False to True. This option will be passed on to the google-chrome process and may resolve your issue. -->

## How to configure a proxy

The URLDownloader service can be configured to use many proxies (or not) and allow the submitting user to pick from a list of proxies. If you want to force a proxy, you can also have a single entry in the list of choices, and that will make it mandatory. URLDownloader does not rely on the system configuration because we have situations where we have multiple proxies and want to fetch content from different places. It could also happen that the proxies from which we want to fetch be different be different from the proxy used by the rest of the system.

You can configure proxy settings from the URLDownloader configuration page in the **Service Variables** section.
Two parameters are important, the first one being `proxies [json]` and the second being `proxy [list]`. It is easier to understand their relationship by starting with the `proxies [json]`, which should be found under the service variables toward the bottom of the page.

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

## Modifying Browser Parameters

You can configure the following browser settings in URLDownloader:

- User agent(`user_agent`): This is the value of `User-Agent` in request headers.
- Window size(`window_size`): The screen resolution of the browser.
- Request headers (`headers`/`request_headers`): Request headers used to fetch URLs.

Administrators can set the default values for these settings from the URLDownloader configuration page in the **Service Variables** section.
These settings will be used by every single submissions to URLDownloader.

Here is an example for `default_browser_settings [json]` service variable:

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
Here is an example:

```
# Assemblyline URI file 1
uri: https://sample_webpage.com/

browser_settings:
    window_size: 1280x720
    user_agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36

# request headers
headers:
    sec-ch-ua-platform: Windows
```

The values set by the URI file will override the values set by `default_browser_settings`.
If `headers` value is set in the URI file, its value overwrites the service parameter values set in `default_browser_settings.request_headers`.

Using the above `default_browser_settings` and _Assemblyline URI file 1_ as an example, these will be the settings used by URLDownloader:

```
uri: https://sample_webpage.com/

window_size: 1280x720
user_agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36
request_headers:
    sec-ch-ua-platform: Windows
```

Users have the option to change only the settings that are relevant to them and URLDownloader will use the values in `default_browser_settings` for the rest.
For example, given this URI file:

```
# Assemblyline URI file 2
uri: https://sample_webpage.com/

browser_settings:
    window_size: 2000x2000
```

Combined _Assemblyline URI file 2_ with the `default_browser_settings` stated above, these will be the settings used by URLDownloader:

```
uri: https://sample_webpage.com/

window_size: 2000x2000 # from URI file
user_agent: Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1 # from default settings
request_headers: # from default settings
    "Sec-CH-UA-Mobile": "?1"
```

Users can check the settings used by each submission by looking at the file `Service Results > URLDownloader > Supplementary files > results.json (kangooroo Result Output)`.
