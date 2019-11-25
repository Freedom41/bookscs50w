import os

from flask import Flask, session, render_template, request, redirect, url_for, escape, jsonify
from flask_bcrypt import Bcrypt, generate_password_hash,check_password_hash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import csv
import requests
import xml.etree.ElementTree as et
import json


app = Flask(__name__)
bcrypt = Bcrypt(app)

#Check for goodreads api Key 
if not os.getenv("GOOD_READS"):
    raise RuntimeError("Good reads key not set")

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

#key
key = os.getenv("GOOD_READS")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
#index route
     
@app.route("/")
def index():
    if(session):
        return render_template("userprofile.html")
    return render_template("login.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("/signup.html")

# creates a user and adds them to the database
@app.route("/createuser", methods=["POST"])
def createuser():
    name = request.form.get("name")
    age = request.form.get("age")
    email = request.form.get("email")
    pw = request.form.get("password")
    pwhash = bcrypt.generate_password_hash(pw).decode('utf-8')  
    unique = db.execute('SELECT * FROM users WHERE username =:name or email =:email', {'name': name, "email": email}).fetchall()
    if unique != []: 
        return render_template('error.html', headline="Username and email already in use")
    
    db.execute("INSERT INTO users (username, age, email, password) VALUES (:name, :age, :email, :password)", {"name": name, "age": age, "email": email, "password": pwhash })
    db.commit()
    return render_template("success.html", headline= 'Your account has been created kindly Log In')
    
#logs in a user, uses session for that    
@app.route("/user", methods=["POST"])
def loginuser():
    if request.method == 'POST':
        if not request.form.get("username"):
            return render_template("error.html", headline='Please provide username')

        if not request.form.get("password"):
            return render_template('error.html', headline="Please provide a password")

        name = request.form.get("username")
        pwd = request.form.get("password")
        userdata = db.execute("SELECT * FROM users WHERE username = :name", {"name": name})
        userinfo = userdata.fetchone()

        if userinfo is None:
            return render_template("error.html", headline="You have not signed up, please Sign Up")
        
        if userinfo is not None: 
            pwhash = userinfo['password']
            if check_password_hash(pwhash, pwd):
                session["name"] = name
                session["log"] = True
                return render_template("userprofile.html")    
                            
            return render_template("error.html", headline="Incorrect Username and Password")
        
    return render_template("error.html", headline="Opeartion not successful")

#logs out a user
@app.route("/logout")
def logout(): 
    session.pop('name', None)
    session["log"] = False
    session.clear()
    return render_template("logoutsuccess.html")

#Search Page 
@app.route("/userprofile")
def userprofile():
    if(session):
        user = session['name']
        return render_template("userprofile.html")
    else:    
        return render_template("error.html", headline="Please log in")

@app.route("/search", methods=["POST", 'GET'])
def sicon():
    if(session == False):
        return render_template("error.html", headline="Please log In")
    if request.method == 'POST':
        searchQuery = request.form.get("search")
        text = request.form.get("text")
        
        if request.form.get("search") == None:    
            return render_template("error.html", headline="Kindly select a search query like author,title,isbn")
        
        if searchQuery == "author":
            text = text.lower()
            text = '%' + text + '%'
            books = db.execute('SELECT * FROM books WHERE lower(author) LIKE :text', {'text': text}).fetchall()

        elif searchQuery == "title":
            text = text.lower()
            text = '%' + text + '%'
            books = db.execute('SELECT * FROM books WHERE lower(title) LIKE :text', {'text': text}).fetchall()

        elif searchQuery == "isbn":
            text = text.strip()
            text = '%' + text + '%'
            books = db.execute('SELECT * FROM books WHERE isbn LIKE :text', {'text': text}).fetchall()
        
        l1 = books
        if l1 != []:
            info = []
            for i in l1:
                l2 = []
                l2.append(i[0])
                l2.append(i[2])
                l2.append(i[3])
                info.append(l2)
            return render_template("userprofile.html", info = info)
        return render_template("error.html", headline='404 error No Books avaliable.')
    
    return render_template('userprofile.html')

#Can get book by database id if logged in
@app.route("/books/<int:bookid>")
def book(bookid):
    if(bookid == 1):
        return render_template("error.html", headline="Reserved book id, Select another one")
    if(session):
        booksInfo = db.execute('SELECT * FROM books WHERE id = :id', {'id': bookid}).fetchall()
        if booksInfo == []:
            return render_template("error.html", headline="Book Table id Invalid")
        isbn = booksInfo[0][1]
        book_id = booksInfo[0][0]
        review = db.execute('SELECT * FROM reviews WHERE book_id = :book_id', {'book_id': book_id }).fetchall()
        if review == []:
            return render_template("book.html", title = booksInfo[0][2], author = booksInfo[0][3], isbn = isbn, year=booksInfo[0][4], id = booksInfo[0][0])
        else:
            return render_template("book.html", title = booksInfo[0][2], author = booksInfo[0][3], isbn = isbn, year=booksInfo[0][4], id=booksInfo[0][0],review = review)
    return render_template("error.html", headline="Please log in to continue")

#can get book by ISBN String, full isbn will be required and returns a JSON response
@app.route("/api/<string:isbn>")
def isbn(isbn):
    isbn = isbn.strip()
    booksInfo = db.execute('SELECT * FROM books WHERE isbn = :isbn', {'isbn': isbn}).fetchall()
    if booksInfo == []:
        return render_template("error.html", headline="Invalid ISBN")
    info = []
    for i in booksInfo:
        l2 = []
        l2.append(i[0])
        l2.append(i[2])
        l2.append(i[3])
        l2.append(i[4])
        info.append(l2)
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": key, "isbns": booksInfo[0][1]} )
    result = res.json()
    avgScore = result['books'][0]['average_rating']
    review_counts = result['books'][0]['work_reviews_count']
    info[0].append(avgScore)
    info[0].append(review_counts)
    jsonres = {"Title": info[0][1],"Author": info[0][2],"average_score": info[0][4],"review_count": info[0][5], "Year" : info[0][3], "ISBN" : booksInfo[0][1]}
    return jsonify(jsonres)

# Submits a review, users cannot add reviews to same book
@app.route("/submitreview/<int:id>", methods=["POST"])
def submitreview(id):
    rating = request.form.get('rating')
    text = request.form.get('text')
    if rating == None or text == '':
        return render_template("error.html", headline="Please give review and rating")
    bookid = id
    user_name = session['name']
    review = db.execute('SELECT * FROM reviews WHERE book_id = :book_id', {'book_id': bookid}).fetchall()
    if review == []:
        insertreview = db.execute('INSERT INTO reviews (author, book_id, review_rating, review_text) VALUES (:user_name, :book_id, :rating, :text)', {"user_name": user_name, "book_id": bookid, "rating": rating, "text": text })
        db.commit()
        return render_template("success.html", headline= 'Review Submitted')
    for i in review:
        if i[1] == user_name:
            return render_template("error.html", headline="You cannot submit one review of same book twice")
    insertreview = db.execute('INSERT INTO reviews (author, book_id, review_rating, review_text) VALUES (:user_name, :book_id, :rating, :text)', {"user_name": user_name, "book_id": bookid, "rating": rating, "text": text })
    db.commit()
    return render_template("success.html", headline= 'Review Submitted')
        
@app.route("/error")
def error():    
    return render_template("error.html")

