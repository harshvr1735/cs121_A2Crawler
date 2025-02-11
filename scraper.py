import re
from urllib.parse import urlparse, urldefrag, urljoin, urlunparse
from bs4 import BeautifulSoup
from utils import get_logger
# import urllib.robotparser         not needed, for extra credit ?

logger = get_logger("SCRAPER")
visited_base_url = set()
# visited_depth = {}
visited_urls = {}


def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    links = []

    # checks if we have a valid status code (200 is good) or it has content
    if resp.status_code != 200 or not resp.raw_response:
        return links

    try:
        # parsing html content
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

        # finds all the <a> tags which mean hyperlink and get their href
        # example1: <a href="https://www.ics.uci.edu/contact-us"></a>
        # example2: <a href="about-us"></a>
        for link in soup.find_all('a', href=True):
            href = link['href']  # extracts the link "https://www.ics.uci.edu/contact-us", "about-us"
            complete_url = urljoin(url, href)  # joins it to the base url - "https://www.ics.uci.edu/about-us"
            links.append(complete_url)

    except Exception as e:
        print(f"Error parsing {url}: {e}")

    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        print("IS_VALID")
        parsed = urlparse(url)
        logger.info(f"Checking URL: {url}")
        logger.info(f"Parsed Hostname: {parsed.hostname}")
        if parsed.scheme not in set(["http", "https"]):
            return False

        if not re.match(r".*(\.ics\.uci\.edu|\.cs\.uci\.edu|\.informatics\.uci\.edu|\.stat\.uci\.edu)$", parsed.hostname): ## domain needs to be one of these, allows subdomains

        # if not re.match(r"^(?:.*\.)?(\.ics\.uci\.edu|\.cs\.uci\.edu|\.informatics\.uci\.edu|\.stat\.uci\.edu)$", parsed.hostname):
            return False ## too restrictive, doesnt allow subdomains ^^

        if any(keyword in parsed.query.lower() for keyword in ["ical=", "outlook-ical=", "tribe-bar-date=", "eventdate=", "calendar-view", "date="]):
            return False

        return not re.match( ## removes not wanted file extensions
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
    except TypeError:
        print("TypeError for ", parsed)
        raise
