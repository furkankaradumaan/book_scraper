"""
In this project, we will build a web scraper that collects book
information from the first five pages of the site "http://books.toscrape.com/"
For each book, we will extract the title, price, availability status,
and star rating. And we will save everything in "books.csv" file.

1 -> Column titles for books.csv: Title, Price, Available, Rating
"""

import argparse
from bs4 import BeautifulSoup, Tag
from contextlib import contextmanager
import csv
from dataclasses import dataclass, field
from enum import IntEnum
from functools import reduce
import logging
import re
import requests
from time import sleep, time
from typing import Dict, List, Optional

class Rating(IntEnum):
    """
    This rating class represents the Rating of a book.
    The ratings may be 1-5 stars.
    """
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5
    
    @classmethod
    def from_string(cls, string: str) -> "Rating":
        """
        Gets a string and returns the corresponding Rating object.
        If it does not match anything, function retunds None.
        """
        if string == "One":
            return Rating.ONE_STAR
        if string == "Two":
            return Rating.TWO_STARS
        if string == "Three":
            return Rating.THREE_STARS
        if string == "Four":
            return Rating.FOUR_STARS
        if string == "Five":
            return Rating.FIVE_STARS
        return None
    
    def __str__(self):
        """
        A string representation of Rating object using stars: Rating.value = 2 -> '★★☆☆☆'
        """
        return '\u2605' * self.value + '\u2606' * (5 - self.value)
 
@dataclass
class Book:
    """
    Represents book objects fetched from page.
    """
    title: str
    price: float
    available: bool
    rating: Rating # IntEnum object
    
    def __post_init__(self):
        if self.price < 0.00:
            raise ValueError("Price cannot be negative")
 
@dataclass
class ScraperConfig:
    """
    The configuration settings of the program collected in this class
    """
    base_url: str = field(init=False, default="http://books.toscrape.com/catalogue")
    npages: int
    csv_name: str 
    log_file: str
    log_format: str = field(init=False, default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    log_date_fmt: str = field(init=False, default="%d.%m.%Y %H.%M.%S")
    fields: list = field(init=False, default_factory=lambda:["Title", "Price", "Available", "Rating"])
    rating_map: dict = field(init=False, default_factory=lambda:{"One" : 1, "Two" : 2, "Three" : 3, "Four" : 4, "Five" : 5})
    delay_seconds: float = field(init=False, default=0.4)
    book_counter: int = field(init=False, default=0)
    def __post_init__(self): 
        if not (0 < self.delay_seconds < 5):
            raise ValueError("Delay time must be between 0 and 5.")
        if not self.csv_name.endswith(".csv"):
            raise ValueError("Invalid CSV file name: {self.csv_name}")
        if not self.log_file.endswith(".log"):
            raise ValueError("Invalid log file name: {self.log_file}")
        if self.npages < 0:
            raise ValueError(f"Invalid pages: {self.npages}")
    
    def increment_counter(self):
        self.book_counter += 1

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--csv", default="books.csv")
parser.add_argument("-l", "--log", default="books_scraper_errors.log")
parser.add_argument("-n", "--pages", type=int, default=5)

args = parser.parse_args()

if args.csv:
    csv_name = args.csv
if args.log:
    log_name = args.log
if args.pages:
    npages = args.pages

config = ScraperConfig(csv_name=csv_name, log_file=log_name, npages=npages)

# Make the config settings for logger
logging.basicConfig(filename = config.log_file,
                        level = logging.DEBUG,
                        format = config.log_format,
                        datefmt = config.log_date_fmt,
                        )

logger = logging.getLogger("BookScraper")

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time()
        func(*args, **kwargs)
        end_time = time()
        print(f"Process lasted {end_time - start_time} seconds")
    return wrapper

# Tries to fetch the data in the given URL.
# If the operation completed successfully, returns
# a BeautifulSoup object created with the response of the webpage request
# otherwise print a message and returns None.
def fetch_page_data(url:str, session: requests.Session) -> Optional[BeautifulSoup]:
    
    try:
        response = session.get(url)

        if response.status_code != 200: # get request failed
            logger.warning(f"Request failed with status {response.status_code} : {url}") 
            return None
        else:
            return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url} : {e}")
    
    return None

def print_extracting_text():
    l = ["|", "/", "―", "\\", "|", "/", "―", "\\"]
    ch = l[config.book_counter % 8]

    print(f"[{ch}] Extracting book {config.book_counter + 1}", end="\r")

# Extracts the book information from soup object.
# The data we want to extract is book title, book price (just the numerical value),
# availability status (In stock : True, otherwise False), and book star rating.
def extract_book_info(article: Tag) -> Optional[Book]: 
    
    print_extracting_text()
    # Extract title
    title_tag = article.img
    title = title_tag["alt"] if title_tag else "Unknown"
    
    # Extract price
    price_tag = article.find("p", class_ = "price_color")
    price = price_tag.get_text()[2:] if price_tag else "0.00"
    try:
        price = float(price) if price else 0.00
    except ValueError:
        logger.warning(f"Invalid price has been detected: {price}")
        return None

    availability_tag = article.find("p", class_ = "instock availability")
    if availability_tag:
        available = True if availability_tag.get_text().strip() == "In stock" else False
    else:
        available = False

    rating_tag = article.find("p", class_ = "star-rating")
    if rating_tag:
        rating_text = rating_tag["class"][1]
        rating = Rating.from_string(rating_text)
    
    config.increment_counter()
    # Create a dictionary from the data and return it
    sleep(delay_seconds)
    return Book(title, price, available, rating)

def scrape_books(num_pages: int, session: requests.Session) -> List[Book]:
    
    books = []
    for page_number in range(1, num_pages + 1):
        page_url = f"{config.base_url}/page-{page_number}.html"
        print(f"Scraping page {page_url}")
        
        # Walrus operator!! IMPORTANT
        if not (soup := fetch_page_data(page_url, session)):
            logging.warning(f"File information could not fetched: {page_url}")
            continue
        logger.info(f"File information fetched: {page_url}")
        # Find all article tags
        articles = soup.find_all("article", class_ = "product_pod")
        
        books.extend(list(filter(None, map(extract_book_info, articles))))
        logger.info(f"Books have been added into list. Page: {page_url}")
        sleep(config.delay_seconds)

    return books

def save_to_csv(books: List[Book], csv_name: str) -> None:
    if not books:
        print("No books to save")
        return
    with open(csv_name, "w", encoding = "utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=config.fields)
     
        writer.writeheader()
        for book in books:
            writer.writerow({
                    "Title": book.title,
                    "Price": book.price,
                    "Available": book.available,
                    "Rating": book.rating.value
                    })

    print(f"Saved {len(books)} books to {csv_name}")

def safe_average(container):
    return sum(container) / len(container) if len(container) > 0 else 0.0

def book_analysis(books: List[Book]) -> None:

    print("=" * 100)
    print("BOOKS ANALYSIS".center(100))
    print("=" * 100)

    print("OVERVIEW")
    print("--------")

    total_books = len(books)
    print(f"Total number of books: {total_books}")
    average_price = safe_average(list(map(lambda book: book.price, books)))
    print(f"Average price: £{average_price:.2f}")
    
    book_with_max_price = reduce(lambda book1, book2: book1 if book1.price >= book2.price else book2, books)
    book_with_min_price = reduce(lambda book1, book2: book1 if book1.price <= book2.price else book2, books)
    print(f"Price range: £{book_with_min_price.price} - £{book_with_max_price.price}")

    print(f"The most expensive book: '{book_with_max_price.title}': £{book_with_max_price.price}")
    print(f"The cheaper book: '{book_with_min_price.title}': £{book_with_min_price.price}")

def main():
    print("Starting to scraper...")
    with requests.Session() as session:
        logger.info("Book scraping process started")
        books = scrape_books(config.npages, session)
        logger.info("Books infromation collected")
        save_to_csv(books, config.csv_name)
        logger.info(f"Book scraping process completed: {len(books)}")
        print(f"Scraping completed! Total books: {len(books)}")
        print()
        book_analysis(books)

if __name__ == "__main__":
    main()
