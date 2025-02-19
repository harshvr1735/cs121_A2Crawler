import re
from urllib.parse import urlparse, urldefrag, urljoin, urlunparse
from bs4 import BeautifulSoup
from utils import get_logger
import json
import os


token_shelve = "token_shelve"
logger = get_logger("SCRAPER")
traps = ["/pdf/", "archive.ics.uci.edu", "Nanda", "timeline?", "version=", "action=login", "action=download", "ics.uci.edu/events", "isg.ics.uci.edu/events/tag/talks/day", "share=facebook", "share=twitter", ".pdf", ".ps"]


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

    already_visited = check_if_visited_page(url)
    if already_visited:
        return links

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
            tokenizer(url, soup)

        except Exception as e:
            print(f"Error parsing {url}: {e}")

    links = list(set(links))  # removes duplicates
    return links


def check_if_visited_page(url) -> bool:
    """
    Checks if the page has already been visited.
    returns an bool value based on status.
    """
    try:

        if not os.path.exists("all_webpage_count.txt"):
            open("all_webpage_count.txt", "w").close()
            open("all_webpage_count_no_stopwords.txt", "w").close()

        visited_urls = set()
        decoded_url = url.replace("%7E", "~") ## converts %7E to ~
        base_url, frag = urldefrag(decoded_url)
        base_url = base_url.replace("/www.", "/")

        try:
            with open("all_webpage_count.txt", "r") as file:
                for line in file:
                    v_url = line.split(',')[0].strip()
                    visited_urls.add(v_url.replace("%7E", "~"))

        except Exception as e:
            logger.info(f"{e}: {url}")

        if base_url in visited_urls:
            logger.info(f"Already visited: {url}")
            return True

    except Exception as e:
        logger.error(f"Error checking visited URLs: {e}")
        return True

    return False


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
        decoded_url = url_decoder(complete_url)  # Converts %7E to ~ in urls so that urls that are encoded do not get duplicated
        clean_url, _ = urldefrag(decoded_url)  # Remove fragments
        normal_url = normalize_url(clean_url)
        if normal_url:
            links.append(normal_url)
    return links


def url_decoder(complete_url):
    decoded_url = complete_url.replace("%7E", "~")
    return decoded_url


def normalize_url(url):
    """
    Normalizes URLs to remove redundant parts
    """
    parsed_url = urlparse(url)

    hostname = parsed_url.hostname
    if hostname and hostname.startswith("www."):
        hostname = hostname[4:]

    path_segments = []
    for seg in parsed_url.path.split('/'):
        if seg and (not path_segments or seg != path_segments[-1]):
            path_segments.append(seg)

    normal_path = '/'.join(path_segments)
    return urlunparse(parsed_url._replace(netloc=hostname, path=normal_path))


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False

        # Ensures that there is a hostname before examining the URL
        if not parsed.hostname:
            return False

        # Domain needs to be one of these, allows subdomains
        if not re.match(r"(.*\.)?(ics|cs|informatics|stat)\.uci\.edu",
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

        # Ensures that the crawler avoids potential traps
        for t in traps:
            if t in parsed.geturl():
                return False

        # Returns the URL if it doesn't end with any of these extension tags
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico|img|sql|ipynb|war|bam|mpg|ppsx"
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


def tokenizer(url, soup):
    doc_words = (soup.get_text(separator=" ")).split()
    stopwords_set = {"a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
                     "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
                     "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
                     "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
                     "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
                     "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
                     "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more",
                     "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
                     "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
                     "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
                     "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they",
                     "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
                     "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
                     "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom",
                     "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
                     "your", "yours", "yourself", "yourselves"}
    token_frequencies = {}
    token_frequencies_no_stop_words = {}

    url_words = 0
    url_words_no_stop_words = 0

    for token in doc_words:
        token = token.lower()
        url_words += 1
        if token not in token_frequencies:
            token_frequencies[token] = 1
        else:
            token_frequencies[token] += 1
        if token not in stopwords_set:
            url_words_no_stop_words += 1
            if token not in token_frequencies_no_stop_words:
                token_frequencies_no_stop_words[token] = 1
            else:
                token_frequencies_no_stop_words[token] += 1
    try:
        token_frequencies_json = "token_frequencies.json"
        token_frequencies_nostop_json = "token_frequencies_nostop.json"
        with open(token_frequencies_json, "r") as f:
            old_frequencies = json.load(f)

        with open(token_frequencies_nostop_json, "r") as f:
            old_frequencies_nostop = json.load(f)

    except FileNotFoundError:
        old_frequencies = {}
        old_frequencies_nostop = {}

    for token, count in token_frequencies.items():
        if token in old_frequencies:
            old_frequencies[token] += count
        else:
            old_frequencies[token] = count

    for token, count in token_frequencies_no_stop_words.items():
        if token in old_frequencies_nostop:
            old_frequencies_nostop[token] += count
        else:
            old_frequencies_nostop[token] = count

    with open(token_frequencies_json, "w") as f:
        json.dump(old_frequencies, f)

    with open(token_frequencies_nostop_json, "w") as f:
        json.dump(old_frequencies_nostop, f)

    all_webpage_count = "all_webpage_count.txt"
    with open(all_webpage_count, "a") as file:
        text_to_write = f"{url},{url_words}\n"
        file.write(text_to_write)

    all_webpage_count_no_stopwords = "all_webpage_count_no_stopwords.txt"

    with open(all_webpage_count_no_stopwords, "a") as file:
        text_to_write = f"{url},{url_words_no_stop_words}\n"
        file.write(text_to_write)
