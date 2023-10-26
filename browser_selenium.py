from common import FuzzedBrowser
import logging
from browser_adapters.libcef import LibcefSeleniumBrowser
from browser_adapters.chromium import ChromiumSeleniumBrowser
from browser_adapters.webkit import WebKitSeleniumBrowser
from browser_adapters.firefox import FirefoxSeleniumBrowser
from browser_adapters.webkit_random_walk import WebKitRandomVisitWebsitesBrowser


def get_browser(threadId, browser_name, timeout) -> FuzzedBrowser:
    browser = None
    timeout = int(timeout)
    if browser_name == "webkitgtk":
        browser = WebKitSeleniumBrowser(threadId, timeout, "gtk")
    elif browser_name == "webkitwpe":
        browser = WebKitSeleniumBrowser(threadId, timeout, "wpe")
    elif browser_name == "libcef":
        browser = LibcefSeleniumBrowser(threadId, timeout)
    elif browser_name == "chromium":
        browser = ChromiumSeleniumBrowser(threadId, timeout)
    elif browser_name == 'firefox':
        browser = FirefoxSeleniumBrowser(threadId, timeout)
    elif browser_name == "webkitrandomvisit":
        browser = WebKitRandomVisitWebsitesBrowser(threadId, timeout)
    else:
        logging.error(f"[{threadId}]: invalid browser: {browser_name}")
        exit()
    assert browser is not None
    return browser
