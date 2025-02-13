import re
from urllib.parse import urlparse, urldefrag, urljoin, urlunparse
from bs4 import BeautifulSoup
from utils import get_logger

# import urllib.robotparser         not needed, for extra credit ?

logger = get_logger("SCRAPER")
visited_base_url = set()
# visited_depth = {}
visited_urls = {}


## wics.ics.uci.edu/events counts as a trap possibly? should blacklist it
## wiki.ics.uci.edu has a lot of pages where theyre just wiki revisions, but its possible to escape them


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

    num = is_valid_response(resp)

    if num == 4:
        return links
    elif num == 3:
        redirected_url = resp.raw_response.url
        if is_valid(redirected_url):
            links.append(redirected_url)
    elif num == 2:
        try:
            # parsing html content
            soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

            if not has_sufficient_content(soup):
                return links

            if has_nofollow_meta(soup):
                return links

            links = extract_hyperlinks(url, soup)

        except Exception as e:
            print(f"Error parsing {url}: {e}")

    links = list(set(links))  # removes duplicates
    return links


def is_valid_response(resp) -> int:
    """
    Checks if the response is valid (status 200-399 and contains content).
    returns an int 2 - 200, 3 - 300, 4 - 400
    """
    if not resp.raw_response:
        return 4

    if 200 <= resp.status < 400:
        if resp.status >= 300:  # Handle redirects
            return 3
        if bool(resp.raw_response.content.strip()):  # Ensure content is not empty
            return 2
    return 4


def has_sufficient_content(soup):
    """
    Ensures the page has enough textual content to be worth crawling.
    """
    doc_words = (soup.get_text(separator=" ")).split()
    if len(doc_words) < 100:
        return False
    return True


def has_nofollow_meta(soup):
    """
    Checks if the page has a nofollow meta tag
    """
    robot = soup.find('meta', attrs={'name': 'robots'})
    if robot and 'nofollow' in robot.get('content', '').lower():
        return robot and 'nofollow' in robot.get('content', '').lower()


def extract_hyperlinks(url, soup):
    """
    Extracts hyperlinks from the parsed HTML content
    """
    links = []
    # finds all the <a> tags which mean hyperlink and get their href
    # example1: <a href="https://www.ics.uci.edu/contact-us"></a>
    # example2: <a href="about-us"></a>
    for link in soup.find_all('a', href=True):
        raw_link = link['href']  # extracts the link "https://www.ics.uci.edu/contact-us", "about-us"
        complete_url = urljoin(url, raw_link)  # joins it to the base url - "https://www.ics.uci.edu/about-us"
        clean_url, _ = urldefrag(complete_url)  # Remove fragments
        normal_url = normalize_url(clean_url)
        if normal_url:
            links.append(normal_url)
    return links


def normalize_url(url):
    """
    Normalizes URLs to remove redundant parts
    """
    parsed_url = urlparse(url)
    path_segments = []
    for seg in parsed_url.path.split('/'):
        if seg and (not path_segments or seg != path_segments[-1]):
            path_segments.append(seg)

    normal_path = '/'.join(path_segments)
    return urlunparse(parsed_url._replace(path=normal_path))


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        # Domain needs to be one of these, allows subdomains
        if not re.match(r".*(\.ics\.uci\.edu|\.cs\.uci\.edu|\.informatics\.uci\.edu|\.stat\.uci\.edu)$",
                        parsed.hostname):  # domain needs to be one of these, allows subdomains
            return False

        # Domain can't have any "2000-01-03" etc
        if re.search(r"\b\d{4}-\d{2}-\d{2}\b", parsed.path):
            logger.info(f"Date in url: {url}")
            return False

        # Removes unwanted tags in the URL, such as calendars or excessive dates
        if any(keyword in parsed.query.lower() for keyword in
               ["ical=", "outlook-ical=", "tribe-bar-date=", "eventdate=", "calendar-view", "date="]):
            return False

        # Returns the URL if it doesn't end with any of these extension tags
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico|img"
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
