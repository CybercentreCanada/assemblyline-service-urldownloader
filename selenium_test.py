import json
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
# chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--network_log.preserve-log=true")

chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
driver = webdriver.Chrome(options=chrome_options)


site = "https://slashdot.org"

if len(sys.argv) == 2:
    site = sys.argv[1]

driver.get(site)

perf = driver.get_log("performance")
for p in perf:
    m = json.loads(p["message"])["message"]
    if "redirectResponse" in m["params"]:
        if "location" in m["params"]["redirectResponse"]["headers"]:
            redirect_location = m["params"]["redirectResponse"]["headers"]["location"]
        elif "Location" in m["params"]["redirectResponse"]["headers"]:
            redirect_location = m["params"]["redirectResponse"]["headers"]["Location"]
        remote_ip = m["params"]["redirectResponse"]["remoteIPAddress"]
        print(
            "*****",
            m["params"]["redirectResponse"]["url"],
            f"({remote_ip}) ->" if remote_ip else "->",
            redirect_location,
            f'({m["params"]["redirectResponse"]["status"]})',
        )
driver.quit()
