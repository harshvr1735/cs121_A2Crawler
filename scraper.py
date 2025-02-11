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
    links = []
    # base_url = (urlparse(url))._replace(query="").geturl()
    # if base_url in visited_depth:
    #     if visited_depth[base_url] > 10:
    #         logger.info(f"BASE_URL DEPTH TOO MUCH: {base_url}")
    #         return []
    #     else:
    #         visited_depth[base_url] += 1
    # else:
    #     logger.info(f"BASE_URL DEPTH CREATED: {base_url}")
    #     visited_base_url.add(url)
    #     visited_depth[base_url] = 0

    if url in visited_base_url:
        logger.info(f"Already visited: {url}")
    # # if base_url in visited_base_url:
        return []
    visited_base_url.add(url)
    # parsed = urlparse(url)
    # path = parsed.path.lower()
    # domain = parsed.hostname.lower()

    # if (domain, path) in visited_urls and visited_urls[(domain, path)] >= 5:
    #     logger.info(f"skkipping bc of the path exceded: {url}")
    #     return []

    # if (domain, path) not in visited_urls:
    #     visited_urls[(domain, path)] = 0
    # visited_urls[(domain, path)] += 1

    # if url in visited_base_url:
    # # if base_url in visited_base_url:
    #     # print("IN BASE? URL")
    #     return []
    # visited_base_url.add(url)

    if resp.status == 200:
        try: 
            content = resp.raw_response.content ## needs to be the links only
            if not content.strip():
                # print("NO CONTENT")
                logger.info(f"No content: {url}")
                return []
            
            content_soup = BeautifulSoup(content, 'html.parser')

            ## stops the scraper scraping pages of little content
            doc_words = (content_soup.get_text(separator=" ")).split() ## makes sure that the page is useful
            if len(doc_words) < 100: ## need more than 50 words in body for it to count
                # print("SMALL PAGE")
                logger.info(f"Not enough text content: {url}")
                return []
            
            text_len = 0
            for word in doc_words:
                text_len += len(word)
            doc_len = len(str(content_soup))

            if (doc_len > 0): ## finds ratio of html to actual body text
                ratio = text_len / doc_len
            else:
                ratio = 0

            # if ratio < 0.1: ##omfg why is the main pages too much HTML.
            #     print("TOO MUCH HTML")
            #     return []

### no-follow meta tags
            robot = content_soup.find('meta', attrs={'name': 'robots'})
            if robot and 'nofollow' in robot.get('content', '').lower():
                logger.info(f"Skipping bc of nofollow meta tag: {url}")
                return []

            for anchor in content_soup.find_all('a', href=True):
                link = anchor['href']
                # logger.info(f"CHECKING URL: {link}")

                ## had some issues with joining relative links compounding
                full_url = urljoin(url, link)
                parsed_url = urlparse(full_url)

                path_segments = []
                for seg in parsed_url.path.split('/'):
                    if seg and (not path_segments or seg != path_segments[-1]):
                        path_segments.append(seg)

                normal_path = '/'.join(path_segments)
                c_url = urlunparse(parsed_url._replace(path=normal_path))

                # full_url = urljoin(url, link) ## in the case where it drags something like "/browse-informatics/site-map/" instead of full link
                
                logger.info(f"FULL URL: {c_url}")
                clean_url, frag = urldefrag(c_url) ## removes fragments (from canvas)
                
                # logger.info(f"DEFRAGGED URL: {clean_url}")
                links.append(clean_url)

        except Exception as e:
            print(f"Error parsing {url}: {e}")

    links = list(set(links))
    # links = extract_next_links(url, resp)
    valid = [link for link in links if is_valid(link)]
    logger.info(f"{len(valid)} valid links from {url}: {valid}")
    return valid
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
    return list()

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        # print("IS_VALID")
        parsed = urlparse(url)
        # logger.info(f"Checking URL: {url}")
        # logger.info(f"Parsed Hostname: {parsed.hostname}")
        if parsed.scheme not in set(["http", "https"]):
            return False

        if not re.match(r".*(\.ics\.uci\.edu|\.cs\.uci\.edu|\.informatics\.uci\.edu|\.stat\.uci\.edu)$", parsed.hostname): ## domain needs to be one of these, allows subdomains

        # if not re.match(r"^(?:.*\.)?(\.ics\.uci\.edu|\.cs\.uci\.edu|\.informatics\.uci\.edu|\.stat\.uci\.edu)$", parsed.hostname):
            return False ## too restrictive, doesnt allow subdomains ^^
        if re.search(r"\b\d{4}-\d{2}-\d{2}\b", parsed.path):
            logger.info(f"Date in url: {url}")
            return False
            
        if any(keyword in parsed.query.lower() for keyword in ["ical=", "outlook-ical=", "tribe-bar-date=", "eventdate=", "calendar-view", "date="]):
            return False

        return not re.match( ## removes not wanted file extensions
            r".*\.(css|js|bmp|gif|jpe?g|ico|img"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())
    except TypeError:
        print ("TypeError for ", parsed)
        raise
