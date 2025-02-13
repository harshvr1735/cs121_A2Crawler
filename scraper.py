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

# TODO: break everything into different helper functions

def scraper(url, resp):
    links = []

    if url in visited_base_url:
        logger.info(f"Already visited: {url}")
        return []
    visited_base_url.add(url)

    if resp.status == 200:  # TODO: NEED TO ALLOW REDIRECTS! 200-399
        try:
            content = resp.raw_response.content
            if not content.strip():
                logger.info(f"No content: {url}")
                return []

            content_soup = BeautifulSoup(content, 'html.parser')

            ## Stops the scraper scraping pages of little content (< 100 words)
            doc_words = (content_soup.get_text(separator=" ")).split()
            if len(doc_words) < 100:
                logger.info(f"Not enough text content: {url}")
                return []


            ### Scraper does not scrape if page contains no-follow meta tags
            robot = content_soup.find('meta', attrs={'name': 'robots'})
            if robot and 'nofollow' in robot.get('content', '').lower():
                logger.info(f"Skipping bc of nofollow meta tag: {url}")
                return []

            for anchor in content_soup.find_all('a', href=True):
                link = anchor['href']

                ## Had some issues with joining relative links compounding
                ## Removes copies of segments that might be repeated
                full_url = urljoin(url, link)
                parsed_url = urlparse(full_url)

                path_segments = []
                for seg in parsed_url.path.split('/'):
                    if seg and (not path_segments or seg != path_segments[-1]):
                        path_segments.append(seg)

                normal_path = '/'.join(path_segments)
                c_url = urlunparse(parsed_url._replace(path=normal_path))

                logger.info(f"FULL URL: {c_url}")
                clean_url, frag = urldefrag(c_url)  ## Removes fragments (from canvas)

                links.append(clean_url)

        except Exception as e:
            print(f"Error parsing {url}: {e}")

    links = list(set(links))
    valid = [link for link in links if is_valid(link)]
    logger.info(f"{len(valid)} valid links from {url}: {valid}")
    return valid
    # links = extract_next_links(url, resp)
    # return [link for link in links if is_valid(link)]


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

            # finds all the <a> tags which mean hyperlink and get their href
            # example1: <a href="https://www.ics.uci.edu/contact-us"></a>
            # example2: <a href="about-us"></a>
            for link in soup.find_all('a', href=True):
                href = link['href']  # extracts the link "https://www.ics.uci.edu/contact-us", "about-us"
                complete_url = urljoin(url, href)  # joins it to the base url - "https://www.ics.uci.edu/about-us"
                if is_valid(complete_url):
                    links.append(complete_url)

        except Exception as e:
            print(f"Error parsing {url}: {e}")

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
