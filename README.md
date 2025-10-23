# BOOK SCRAPER PROJECT USING PYTHON

## Project Overview
This project scrapes book data from page "http://books.toscrape.com/catalogue".
It scrapes the title, price, availability state, and rating information for each book.
It stores all the information in a CSV file. Also log messages are recorded in a log file.

## Command Line Arguments
You can specify the name of the CSV file by command line: [-c | --csv] <filename>.
The file name MUST end with ".csv". the default value for the CSV file is "books.csv"

You can specify the name of the log file by command line: [-l | --log] <filename>.
The file name MUST end with ".log".

You can also specify how many pages of books you want to scrape: [-n | --pages] <npages>.
