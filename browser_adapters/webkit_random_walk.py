from common import FuzzedBrowser

import os
import random
import logging
import signal
import psutil
import copy

from selenium.webdriver.webkitgtk import webdriver, options
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class WebKitRandomVisitWebsitesBrowser(FuzzedBrowser):
    def __init__(self, thread_id, timeout, port="gtk"):
        self.thread_id = thread_id
        self.timeout_sec = int(timeout) / 1000
        self.port = port
        self.browser = None
        self.tmp_dir = "/tmp/webkittmpdir" + str(self.thread_id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.msg_path = self.tmp_dir + "/tmp_log"
        self.websites = get_websites()

        # close the browser with this probability
        self.close_browser_prob = 0.01
        if "CLOSE_BROWSER_PROB" in os.environ:
            self.close_browser_prob = float(os.environ["CLOSE_BROWSER_PROB"])

        # configure for launching browser
        self.caps = DesiredCapabilities.WEBKITGTK.copy()
        self.caps["pageLoadStrategy"] = "normal"
        self.option = options.Options()
        self.option.add_argument("--automation")
        self.termination_log = None
        if "WEBKIT_WEBDRIVER_PATH" in os.environ:
            self.webkit_driver_path = os.environ["WEBKIT_WEBDRIVER_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set WEBKIT_WEBDRIVER_PATH env var")
            exit(1)
        if "WEBKIT_BINARY_PATH" in os.environ:
            self.option.binary_location = os.environ["WEBKIT_BINARY_PATH"]
        else:
            logging.error(f"[{thread_id}]: didn't set WEBKIT_BINARY_PATH env var")
            exit(1)
        os.environ["FUZZER_TMP_PATH"] = self.msg_path
        self.launch_browser()

    def __del__(self):
        try:
            self.close_browser()
        except:
            pass

    def launch_browser(self):
        logging.info(f"[{self.thread_id}]: start launching")
        try:
            self.browser = webdriver.WebDriver(
                executable_path=self.webkit_driver_path,
                options=self.option,
                # desired_capabilities=self.caps,
                service_log_path=self.msg_path)
            self.browser.set_page_load_timeout(self.timeout_sec)
            self.browser.command_executor.set_timeout(self.timeout_sec)
            logging.info(f"[{self.thread_id}]: end launching")
            webdriver_pid = self.browser.service.process.pid
            logging.info(f"[{self.thread_id}]: webkit pid: {webdriver_pid}")
        except KeyboardInterrupt as e:
            logging.info(f"interrupted by user: {e}")
        except BaseException as e:
            logging.error(f"[{self.thread_id}]: cannot launch browser. {repr(e)}")
            # raise
            logging.error(f"[{self.thread_id}]: try again")
            # exit(1)
            self.launch_browser()

    def close_browser(self):
        webdriver_pid = self.browser.service.process.pid
        process = psutil.Process(webdriver_pid)
        child_procs = process.children(recursive=True)
        try:
            self.browser.quit()
            logging.info(f"[{self.thread_id}]: successfully quit")
        except BaseException as e:
            logging.info(f"[{self.thread_id}]: cannot normally quit. cause: {repr(e)}")
        logging.info(f"[{self.thread_id}]: try to kill webdriver pid: {webdriver_pid}")
        try:
            os.kill(webdriver_pid, signal.SIGKILL)
            logging.info(f"[{self.thread_id}]: successfully kill webdriver pid: {webdriver_pid}")
        except ProcessLookupError as e:
            pass
        except BaseException as e:
            logging.info(
                f"[{self.thread_id}]: cannot kill webdriver pid :{webdriver_pid}; cause: {repr(e)}")
        for pid in child_procs:
            logging.info(f"[{self.thread_id}]: try to kill pid: {pid.pid}")
            try:
                os.kill(pid.pid, signal.SIGKILL)
                logging.info(f"[{self.thread_id}]: successfully kill pid {pid.pid}")
            except ProcessLookupError as e:
                pass
            except BaseException as e:
                logging.info(f"[{self.thread_id}]: cannot kill {pid.pid}; cause: {repr(e)}")
        self.browser = None

    def close_all_tabs(self):
        try:
            handles = self.browser.window_handles
            if len(handles) == 1:
                return
            handle_0 = handles[0]
            for handle in handles:
                if handle_0 != handle:
                    self.browser.switch_to.window(handle)
                    self.browser.close()
            self.browser.switch_to.window(handle_0)
        except BaseException as e:
            raise

    def new_page(self):
        try:
            # handles = self.browser.window_handles
            # for handle in handles:
            #     if self.main_window != handle:
            #         self.browser.switch_to.window(handle)
            #         self.browser.close()
            # self.browser.switch_to.window(self.main_window)
            # self.browser.execute_script("window.open('','_blank');")
            self.close_all_tabs()
            self.browser.switch_to.window(self.browser.window_handles[0])
            self.browser.execute_script("window.open('','_blank');")
            self.browser.switch_to.window(self.browser.window_handles[1])
        except UnexpectedAlertPresentException as e:
            self.browser.switch_to.alert.accept()
            self.new_page()
        except BaseException as e:
            logging.error(
                f"[{self.thread_id}]: cannot create a new page, try to restart the browser. reason: {repr(e)}")
            logging.error(
                f"[{self.thread_id}]: {self.message()}"
            )
            self.close_browser()
            self.launch_browser()
            self.new_page()

    def ready(self):
        if self.browser is None:
            self.launch_browser()
        else:
            try:
                self.browser.switch_to.alert.accept()
            except BaseException as e:
                pass
            try:
                r = random.random()
                if r < self.close_browser_prob:
                    logging.info(
                        f"restart browser because the random pick: {r} {self.close_browser_prob}")
                    self.close_browser()
                    self.launch_browser()
                self.new_page()
            except BaseException as e:
                logging.error(f"[{self.thread_id}]: cannot new a page. {repr(e)}")
                self.close_browser()
                self.launch_browser()
                self.new_page()

    def clone(self):
        cloned = copy.copy(self)
        cloned.browser = None
        return cloned

    def get_random_website(self):
        if random.random() > 0.75:
            return self.websites[random.randint(0, len(self.websites) - 1)]
        else:
            try:
                elems = self.browser.find_elements_by_xpath("//*[@href]")
                # elems = self.browser.find_elements_by_tag_name('a')
                # elems = self.browser.find_elements_by_partial_link_text("")
                print(elems)
                if len(elems) == 0:
                    return self.websites[random.randint(0, len(self.websites) - 1)]
                else:
                    path = elems[random.randint(0, len(elems) - 1)].get_attribute("href")
                    print(path)
                    return path
            except BaseException as e:
                logging.error(f"[{self.thread_id}]: websites error?. {repr(e)}")
                self.close_browser()
                self.launch_browser()
                return self.websites[random.randint(0, len(self.websites) - 1)]

    def fuzz(self, path: str):
        while True:
            self.ready()
            self.true_fuzz(self.get_random_website())

    def true_fuzz(self, path: str) -> bool:
        print(path)
        try:
            self.browser.get(path)
            print(self.browser.title)
            return True
        except UnexpectedAlertPresentException as e:
            logging.info(f"[{self.thread_id}]: {repr(e)}!")
            self.browser.switch_to.alert.accept()
            return True
        except TimeoutException as e:
            logging.info(f"[{self.thread_id}]: timeout, {repr(e)}!")
            try:
                self.browser.close()
            except BaseException as e:
                logging.info(
                    f"[{self.thread_id}]: timeout, but cannot close current window. {repr(e)}")
                self.close_browser()
                self.launch_browser()
            return True
        except BaseException as e:
            try:
                logging.info(f"[{self.thread_id}]: not finish, because: {repr(e)}")
                self.browser.close()
                logging.info(f"[{self.thread_id}]: browser can be closed!")
                return True
            except WebDriverException as e:
                logging.info(f"[{self.thread_id}]: crash! WebDriverException: {repr(e)}")
                self.termination_log = self.get_log()
                self.close_browser()
                self.launch_browser()
                return False

    def message(self) -> str:
        if self.termination_log:
            tmp = self.termination_log
            self.termination_log = None
            return tmp
        else:
            return self.get_log()

    def get_log(self) -> str:
        try:
            with open(self.msg_path, "r") as f:
                return f.read()
        except IOError as e:
            return f"[{self.thread_id}]: fail to open msg_path. {repr(e)}"


def get_websites():
    return ['https://www.google.com', 'https://www.youtube.com', 'https://www.baidu.com',
            'https://www.zhihu.com', 'https://www.facebook.com', 'https://www.taobao.com',
            'https://www.sogou.com', 'https://www.163.com', 'https://www.tmall.com',
            'https://www.amazon.com', 'https://www.qq.com', 'https://www.yahoo.com',
            'https://www.so.com',
            'https://www.soso.com', 'https://www.weibo.com', 'https://www.360.cn',
            'https://www.wikipedia.org', 'https://www.zoom.us', 'https://www.instagram.com',
            'https://www.tianya.cn', 'https://www.live.com', 'https://www.bilibili.com',
            'https://www.netflix.com', 'https://www.reddit.com', 'https://www.1688.com',
            'https://www.microsoft.com', 'https://www.office.com', 'https://www.niuche.com',
            'https://www.dedecms.com', 'https://www.sina.com.cn', 'https://www.foodmate.net',
            'https://www.canva.com', 'https://www.pchouse.com.cn', 'https://www.wkzuche.com',
            'https://www.csdn.net', 'https://www.myshopify.com', 'https://www.naver.com',
            'https://www.google.com.hk', 'https://www.jmw.com.cn', 'https://www.bing.com',
            'https://www.twitter.com', 'https://www.vk.com', 'https://www.yahoo.co.jp',
            'https://www.microsoftonline.com', 'https://www.cdstm.cn', 'https://www.bongacams.com',
            'https://www.sharepoint.com', 'https://www.jd.com', 'https://www.chaturbate.com',
            'https://www.hubspot.com', 'https://www.sohu.com', 'https://www.linkedin.com',
            'https://www.adobe.com', 'https://www.twitch.tv', 'https://www.amazon.in',
            'https://www.tiktok.com', 'https://www.ebay.com', 'https://www.amazon.co.jp',
            'https://www.yandex.ru', 'https://www.whatsapp.com', 'https://www.okezone.com',
            'https://www.aliexpress.com', 'https://www.alipay.com', 'https://www.cnblogs.com',
            'https://www.fiverr.com', 'https://www.douban.com', 'https://www.tradingview.com',
            'https://www.ca168.com', 'https://www.indeed.com', 'https://www.okta.com',
            'https://www.youdao.com', 'https://www.mail.ru', 'https://www.hao123.com',
            'https://www.etsy.com', 'https://www.blogger.com', 'https://www.msn.com',
            'https://www.dropbox.com', 'https://www.wordpress.com', 'https://www.zoho.com',
            'https://www.opensea.io', 'https://www.google.co.jp', 'https://www.liputan6.com',
            'https://www.google.de', 'https://www.amazonaws.com', 'https://www.google.co.in',
            'https://www.google.cn', 'https://www.imdb.com', 'https://www.spotify.com',
            'https://www.telegram.org', 'https://www.pikiran-rakyat.com', 'https://www.chase.com',
            'https://www.chinaz.com', 'https://www.jianshu.com', 'https://www.daum.net',
            'https://www.google.com.br', 'https://www.tribunnews.com', 'https://www.pornhub.com',
            'https://www.fandom.com', 'https://www.wordpress.org', 'https://www.paypal.com',
            'https://www.flipkart.com', 'https://www.cnn.com', 'https://www.amazon.de',
            'https://www.github.com', 'https://www.google.fr', 'https://www.digifinex.com',
            'https://www.zendesk.com', 'https://www.zillow.com', 'https://www.deepl.com',
            'https://www.grammarly.com', 'https://www.eastmoney.com', 'https://www.duckduckgo.com',
            'https://www.roblox.com', 'https://www.wix.com', 'https://www.shutterstock.com',
            'https://www.imgur.com', 'https://www.xvideos.com', 'https://www.ok.ru',
            'https://www.toutiao.com', 'https://www.walmart.com', 'https://www.t.me',
            'https://www.force.com', 'https://www.amazon.co.uk', 'https://www.xhamster.com',
            'https://www.stackoverflow.com', 'https://www.shimo.im', 'https://www.ilovepdf.com',
            'https://www.bitly.com', 'https://www.wetransfer.com', 'https://www.mailchimp.com',
            'https://www.booking.com', 'https://www.calendly.com', 'https://www.google.ru',
            'https://www.indiatimes.com', 'https://www.kompas.com', 'https://www.apple.com',
            'https://www.espn.com', 'https://www.bbc.com', 'https://www.coingecko.com',
            'https://www.nytimes.com', 'https://www.speedtest.net', 'https://www.yangkeduo.com',
            'https://www.pinterest.com', 'https://www.envato.com', 'https://www.tistory.com',
            'https://www.savefrom.net', 'https://www.amazon.ca', 'https://www.digikala.com',
            'https://www.detik.com', 'https://www.google.it', 'https://www.pexels.com',
            'https://www.tumblr.com', 'https://www.wellsfargo.com', 'https://www.google.com.sg',
            'https://www.line.me', 'https://www.coinmarketcap.com', 'https://www.zerodha.com',
            'https://www.fedex.com', 'https://www.primevideo.com', 'https://www.investing.com',
            'https://www.americanexpress.com', 'https://www.bbc.co.uk', 'https://www.godaddy.com',
            'https://www.ups.com', 'https://www.vimeo.com', 'https://www.pixnet.net',
            'https://www.youku.com', 'https://www.runoob.com', 'https://www.pixabay.com',
            'https://www.mozilla.org', 'https://www.healthline.com', 'https://www.kakao.com',
            'https://www.mediafire.com', 'https://www.hdfcbank.com', 'https://www.myworkday.com',
            'https://www.smallpdf.com', 'https://www.payoneer.com', 'https://www.iqiyi.com',
            'https://www.google.es', 'https://www.archive.org', 'https://www.ikea.com',
            'https://www.google.co.uk', 'https://www.trendyol.com', 'https://www.salesforce.com',
            'https://www.aliyun.com', 'https://www.instructure.com', 'https://www.box.com',
            'https://www.fidelity.com', 'https://www.usps.com', 'https://www.stackexchange.com',
            'https://www.avito.ru', 'https://www.chess.com', 'https://www.manage.wix.com',
            'https://www.disneyplus.com', 'https://www.soundcloud.com', 'https://www.cnbc.com',
            'https://www.alibaba.com', 'https://www.homedepot.com', 'https://www.google.com.tw',
            'https://www.hbomax.com', 'https://www.behance.net', 'https://www.amazon.com.mx',
            'https://www.nih.gov', 'https://www.weather.com', 'https://www.capitalone.com',
            'https://www.sindonews.com', 'https://www.craigslist.org', 'https://www.padlet.com',
            'https://www.xnxx.com', 'https://www.airbnb.com', 'https://www.glassdoor.com',
            'https://www.hotstar.com', 'https://www.bitfinex.com', 'https://www.docusign.com',
            'https://www.bet9ja.com', 'https://www.istockphoto.com', 'https://www.theguardian.com',
            'https://www.yelp.com', 'https://www.suara.com', 'https://www.worldometers.info',
            'https://www.adp.com', 'https://www.aliexpress.ru', 'https://www.autohome.com.cn',
            'https://www.impact.com', 'https://www.google.com.tr', 'https://www.icicibank.com',
            'https://www.steampowered.com', 'https://www.mercadolibre.com.ar',
            'https://www.coursera.org',
            'https://www.spankbang.com', 'https://www.ebay.de', 'https://www.mercadolibre.com.mx',
            'https://www.lazada.sg', 'https://www.varzesh3.com', 'https://www.dingtalk.com',
            'https://www.researchgate.net', 'https://www.investopedia.com',
            'https://www.mercari.com',
            'https://www.foxnews.com', 'https://www.coupang.com', 'https://www.quora.com',
            'https://www.businessinsider.com', 'https://www.secureserver.net',
            'https://www.shopee.tw',
            'https://www.patch.com', 'https://www.bluehost.com', 'https://www.ameblo.jp',
            'https://www.remove.bg', 'https://www.freepik.com', 'https://www.hulu.com',
            'https://www.shopee.co.id', 'https://www.sahibinden.com', 'https://www.japanpost.jp',
            'https://www.ca.gov', 'https://www.w3schools.com', 'https://www.ltn.com.tw',
            'https://www.intuit.com', 'https://www.skype.com', 'https://www.farfetch.com',
            'https://www.ozon.ru', 'https://www.amazon.fr', 'https://www.redfin.com',
            'https://www.dailymail.co.uk', 'https://www.target.com', 'https://www.bet365.com',
            'https://www.google.ca', 'https://www.youm7.com', 'https://www.hp.com',
            'https://www.cricbuzz.com', 'https://www.bestbuy.com', 'https://www.manoramaonline.com',
            'https://www.ria.ru', 'https://www.telewebion.com', 'https://www.discord.com',
            'https://www.evernote.com', 'https://www.binance.com', 'https://www.bloomberg.com',
            'https://www.bankofamerica.com', 'https://www.leboncoin.fr', 'https://www.douyu.com',
            'https://www.realtor.com', 'https://www.themeforest.net', 'https://www.heavy.com',
            'https://www.uol.com.br', 'https://www.metropoles.com', 'https://www.nicovideo.jp',
            'https://www.umeng.com', 'https://www.pancakeswap.finance', 'https://www.grid.id',
            'https://www.rokna.net', 'https://www.google.com.mx', 'https://www.amazon.es',
            'https://www.ensonhaber.com', 'https://www.wildberries.ru', 'https://www.basecamp.com',
            'https://www.scribd.com', 'https://www.namu.wiki', 'https://www.cloudfront.net',
            'https://www.etoro.com', 'https://www.orange.fr', 'https://www.onlinesbi.com',
            'https://www.mercadolivre.com.br', 'https://www.globo.com', 'https://www.zol.com.cn',
            'https://www.taboola.com', 'https://www.rt.com', 'https://www.samsung.com',
            'https://www.google.com.sa', 'https://www.ndtv.com', 'https://www.wsj.com',
            'https://www.moneycontrol.com', 'https://www.icloud.com', 'https://www.kumparan.com',
            'https://www.nga.cn', 'https://www.squarespace.com', 'https://www.proiezionidiborsa.it',
            'https://www.hootsuite.com', 'https://www.redd.it', 'https://www.docusign.net',
            'https://www.cnet.com', 'https://www.flickr.com', 'https://www.steamcommunity.com',
            'https://www.in.gr', 'https://www.google.com.eg', 'https://www.citi.com',
            'https://www.tencent.com', 'https://www.myworkdayjobs.com', 'https://www.fast.com',
            'https://www.codepen.io', 'https://www.google.co.th', 'https://www.poocoin.app',
            'https://www.rakuten.co.jp', 'https://www.shopee.com.my',
            'https://www.washingtonpost.com',
            'https://www.wise.com', 'https://www.twimg.com', 'https://www.techcrunch.com',
            'https://www.y2mate.com', 'https://www.google.com.ar', 'https://www.allegro.pl',
            'https://www.asriran.com', 'https://www.ssense.com', 'https://www.google.pl',
            'https://www.irs.gov', 'https://www.sciencedirect.com', 'https://www.quillbot.com',
            'https://www.kuronekoyamato.co.jp', 'https://www.filimo.com',
            'https://www.goodreads.com',
            'https://www.asos.com', 'https://www.cvs.com', 'https://www.shaparak.ir',
            'https://www.cj.com',
            'https://www.indiamart.com', 'https://www.razorpay.com', 'https://www.google.co.id',
            'https://www.thesaurus.com', 'https://www.huaban.com', 'https://www.inquirer.net',
            'https://www.cdc.gov', 'https://www.hostgator.com', 'https://www.marketwatch.com',
            'https://www.google.co.kr', 'https://www.constantcontact.com',
            'https://www.ninisite.com',
            'https://www.trustpilot.com', 'https://www.slideshare.net',
            'https://www.smallseotools.com',
            'https://www.naukri.com', 'https://www.aol.com', 'https://www.setn.com',
            'https://www.cloudflare.com', 'https://www.wayfair.com',
            'https://www.donya-e-eqtesad.com',
            'https://www.espncricinfo.com', 'https://www.dell.com', 'https://www.namasha.com',
            'https://www.dailymotion.com', 'https://www.walgreens.com',
            'https://www.smartsheet.com',
            'https://www.shopee.vn', 'https://www.shareasale.com', 'https://www.patreon.com',
            'https://www.bamboohr.com', 'https://www.td.com', 'https://www.wikimedia.org',
            'https://www.amazon.it', 'https://www.allcoolnewz.com', 'https://www.rakuten.com',
            'https://www.reuters.com', 'https://www.protonmail.com', 'https://www.schwab.com',
            'https://www.tripadvisor.com', 'https://www.att.com', 'https://www.fool.com',
            'https://www.delgarm.com', 'https://www.canada.ca', 'https://www.yjc.news',
            'https://www.iqbroker.com', 'https://www.rambler.ru', 'https://www.upwork.com',
            'https://www.dhl.com', 'https://www.patria.org.ve', 'https://www.fardanews.com',
            'https://www.mihoyo.com', 'https://www.ladbible.com', 'https://www.shopee.co.th',
            'https://www.sznews.com', 'https://www.webmd.com', 'https://www.akamaized.net',
            'https://www.ameritrade.com', 'https://www.turkiye.gov.tr',
            'https://www.quip-amazon.com',
            'https://www.cnbeta.com', 'https://www.pipedrive.com', 'https://www.zoho.in',
            'https://www.editor.wix.com', 'https://www.costco.com', 'https://www.macys.com',
            'https://www.medium.com', 'https://www.weebly.com', 'https://www.teachable.com',
            'https://www.onlyfans.com', 'https://www.breitbart.com', 'https://www.pconline.com.cn',
            'https://www.crowdworks.jp', 'https://www.www.gov.uk', 'https://www.merdeka.com',
            'https://www.epicgames.com', 'https://www.weibo.cn', 'https://www.3dmgame.com',
            'https://www.rctiplus.com', 'https://www.nypost.com', 'https://www.yts.mx',
            'https://www.sourceforge.net', 'https://www.vnexpress.net', 'https://www.xfinity.com',
            'https://www.softonic.com', 'https://www.namnak.com', 'https://www.custhelp.com',
            'https://www.reverso.net', 'https://www.premierbet.co.ao', 'https://www.note.com',
            'https://www.a2z.com', 'https://www.webex.com', 'https://www.kapanlagi.com',
            'https://www.bybit.com', 'https://www.quizlet.com', 'https://www.discordapp.com',
            'https://www.qualtrics.com', 'https://www.51job.com', 'https://www.dbs.com.sg',
            'https://www.enimerotiko.gr', 'https://www.ithome.com', 'https://www.oracle.com',
            'https://www.livejournal.com', 'https://www.dianping.com', 'https://www.tmtpost.com',
            'https://www.pinimg.com', 'https://www.sxyprn.com', 'https://www.marriott.com',
            'https://www.indianexpress.com', 'https://www.qoo10.sg', 'https://www.zhaopin.com',
            'https://www.jw.org', 'https://www.expedia.com', 'https://www.udemy.com',
            'https://www.nate.com', 'https://www.whois.com', 'https://www.meesho.com',
            'https://www.nike.com', 'https://www.yeniakit.com.tr', 'https://www.aparat.com',
            'https://www.tabelog.com', 'https://www.nordstrom.com', 'https://www.pinduoduo.com',
            'https://www.udn.com', 'https://www.gamersky.com', 'https://www.moneyforward.com',
            'https://www.as.com', 'https://www.dmm.co.jp', 'https://www.outbrain.com',
            'https://www.usfinf.net', 'https://www.aliyuncs.com', 'https://www.slack.com',
            'https://www.seznam.cz', 'https://www.netsuite.com', 'https://www.al3omk.com',
            'https://www.gismeteo.ru', 'https://www.teambition.com', 'https://www.fc2.com',
            'https://www.amazon.com.au', 'https://www.accuweather.com', 'https://www.usatoday.com',
            'https://www.zara.com', 'https://www.nvidia.com', 'https://www.deviantart.com',
            'https://www.nba.com', 'https://www.abs-cbn.com', 'https://www.royalbank.com']
