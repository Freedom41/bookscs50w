import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


engine = create_engine(os.getenv('DATABASE_URL'))
db = scoped_session(sessionmaker(bind=engine))

def main():
    book = open("books.csv")
    reader = csv.reader(book) 
    #db.execute('CREATE TABLE reviews (id SERIAL PRIMARY KEY, author VARCHAR NOT NULL, book_id INTEGER NOT NULL REFERENCES books, review_rating VARCHAR NOT NULL, review_text VARCHAR NOT NULL)')
    #db.execute('CREATE TABLE users (id SERIAL PRIMARY KEY,username VARCHAR UNIQUE NOT NULL, email VARCHAR UNIQUE NOT NULL, password VARCHAR NOT NULL, age INTEGER NOT NULL)')
    for isbn, title, author, year in reader:
       db.execute('CREATE TABLE books (id SERIAL PRIMARY KEY, isbn VARCHAR NOT NULL, title VARCHAR NOT NULL, author VARCHAR NOT NULL, year VARCHAR NOT NULL)')    
    
    print(f"Added table.")
    db.commit()

if __name__ == "__main__":
    main()


