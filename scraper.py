import re
from urllib.parse import urlparse, urldefrag, urljoin, urlunparse, unquote
from bs4 import BeautifulSoup
from utils import get_logger
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
import shelve
import csv
from nltk.tokenize import word_tokenize

token_shelve = "token_shelve"
logger = get_logger("SCRAPER")
traps = ["/pdf/","archive.ics.uci.edu","Nanda", "grape.ics.uci.edu/wiki/public/timeline?","version=","action=login","action=download","github.com","ics.uci.edu/events", "isg.ics.uci.edu/events/tag/talks/day", "share=facebook", "share=twitter", ".pdf", ".ps"]

def scraper(url, resp):
    links = []

    try:
        visited_urls = set()
        decoded_url = url.replace("%7E", "~") ## converts %7E to ~ 
        base_url, frag = urldefrag(decoded_url)

        try:
            with open("all_webpage_count.txt", "r") as file:
                for line in file:
                    v_url = line.split(',')[0].strip()
                    visited_urls.add(v_url.replace("%7E", "~"))

        except Exception as e:
            logger.info(f"{e}: {url}")

        if base_url in visited_urls:
            logger.info(f"Already visited: {url}")
            return []            

    except Exception as e:
        logger.error(f"Error checking visited URLs: {e}")
        return []

    if "ssh://git@github.com" in url:
        return []

    if resp.status == 200: #TODO: NEED TO ALLOW REDIRECTS! 200-399
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
            tokenizer(url, doc_words)

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
                decoded_url = c_url.replace("%7E", "~")

                clean_url, frag = urldefrag(decoded_url) ## Removes fragments (from canvas)
                logger.info(f"FULL URL: {c_url}")

                links.append(clean_url)

        except Exception as e:
            print(f"Error parsing {url}: {e}")

    links = list(set(links))
    valid = [link for link in links if is_valid(link)]
    logger.info(f"{len(valid)} valid links from {url}: {valid}")
    return valid
    # links = extract_next_links(url, resp)
    # return [link for link in links if is_valid(link)]

def tokenizer(url, doc_words):
    stopwords_set = set(["a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"])

    url_words = 0
    url_words_no_stop_words = 0
    
    with shelve.open("token_shelve", writeback=False) as ts:
        try:
            token_frequencies = ts.get("token_frequencies", {})
            token_frequencies_no_stop_words = ts.get("token_frequencies_no_stop_words", {})

            for token in doc_words:
                token = token.lower()
                url_words += 1

                token_frequencies[token] = token_frequencies.get(token, 0) + 1

                if token not in stopwords_set:
                    url_words_no_stop_words += 1
                    token_frequencies_no_stop_words[token] = token_frequencies_no_stop_words.get(token, 0) + 1

            ts["token_frequencies"] = token_frequencies
            ts["token_frequencies_no_stop_words"] = token_frequencies_no_stop_words
        except KeyboardInterrupt:
            print(f"Shuting down program through KeyboardInterrupt: {url}, {e}")
        except Exception as e:
            print(f"Error in tokenizing: {url}, {e}")
        # print(f"courses freq: {token_frequencies.get('courses', 0)}")
    all_webpage_count = "all_webpage_count.txt"
    with(open(all_webpage_count, "a")) as file:
        text_to_write = f"{url},{url_words}\n"        
        file.write(text_to_write)

    all_webpage_count_no_stopwords = "all_webpage_count_no_stopwords.txt"
    with(open(all_webpage_count_no_stopwords, "a")) as file:
        text_to_write = f"{url},{url_words_no_stop_words}\n"
        file.write(text_to_write)
    ## probably append to a file to keep track and then convert to a csv for our reports? 
    ## and then sort it there bc thats easy implementation

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
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        if not parsed.hostname:
            logger.info(f"No hostname: {url}")
            return False

## Domain needs to be one of these, allows subdomains
        if not re.match(r"(.*\.)?(ics|cs|informatics|stat)\.uci\.edu", parsed.hostname): ## domain needs to be one of these, allows subdomains
            logger.info(f"Not in wanted domain: {url} {parsed.hostname}")
            return False
## Domain can't have any "2000-01-03" etc
        if re.search(r"\b\d{4}-\d{2}-\d{2}\b", parsed.path):
            logger.info(f"Date in url: {url}")
            return False
## Removes unwanted tags in the URL, such as calendars or excessive dates
        if any(keyword in parsed.query.lower() for keyword in ["timeline", "ical=", "outlook-ical=", "tribe-bar-date=", "eventdate=", "calendar-view", "date="]):
            logger.info(f"Calendar in url: {url}")
            return False
        
        for t in traps:
            if t in parsed.geturl():
                logger.info(f"Found a trap in: {url}")
                return False

## Returns the URL if it doesn't end with any of these extension tags
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico|img|sql|ipynb|war|bam|mpg|ppsx|apk|pps"
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
