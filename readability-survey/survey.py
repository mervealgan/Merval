from flask import Flask, render_template, request, jsonify
import sqlite3
import csv
from datetime import datetime

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('sentences.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS allsents
                 (id INTEGER PRIMARY KEY, sentences TEXT, simplified TEXT, votes INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS ratings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, sentence_id INTEGER, rating_original INTEGER, rating_simplified INTEGER, timestamp DATETIME DEFAULT '1970-01-01 00:00:00')''')
    conn.commit()
    conn.close()


def load_csv():
    csv_file = "sents.csv"
    with open(csv_file, "r", encoding="utf8") as f:
        reader = csv.reader(f, delimiter=",")
        header = next(reader)
        data = list(reader)

    ids = [row[0] for row in data]
    sentences = [row[2] for row in data]
    simplifed = [row[3] for row in data]

    return ids, sentences, simplifed

def load_sentences(ids, sentences, simplified):
    conn = sqlite3.connect('sentences.db')
    c = conn.cursor()
    c.executemany("INSERT OR IGNORE INTO allsents (id, sentences, simplified, votes) VALUES (?, ?, ?, 0)", zip(ids, sentences, simplified))
    conn.commit()
    conn.close()

def get_random_sentences():
    conn = sqlite3.connect('sentences.db')
    c = conn.cursor()
    c.execute("SELECT id, sentences, simplified FROM allsents WHERE votes < 5 ORDER BY RANDOM() LIMIT 20")
    sentences = c.fetchall()
    conn.close()
    return sentences

def update_vote(sentence_id):
    conn = sqlite3.connect('sentences.db')
    c = conn.cursor()
    c.execute("UPDATE allsents SET votes = votes + 1 WHERE id = ?", (sentence_id,))
    conn.commit()
    conn.close()

def update_rating(rating, sentence_id):
    conn = sqlite3.connect('sentences.db')
    c = conn.cursor()
    c.execute("UPDATE allsents SET ratings = ratings + ? WHERE id = ?", (rating, sentence_id))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    sentences = get_random_sentences()
    return render_template('poll.html', sentences=sentences)

@app.route('/submit', methods=['POST'])
def submit():
    ratings = request.json
    timestamp = datetime.now()
    for sentence_id, rating_pair in ratings.items():
        save_individual_rating(int(sentence_id), int(rating_pair['original']), int(rating_pair['simplified']), timestamp)
        if((int(rating_pair['original']) != 0) and (int(rating_pair['simplified']) != 0)):
            update_vote(int(sentence_id))

    return jsonify({"status": "success"})

def save_individual_rating(sentence_id, rating_original, rating_simplified, timestamp):
    conn = sqlite3.connect('sentences.db')
    c = conn.cursor()
    c.execute("INSERT INTO ratings (sentence_id, rating_original, rating_simplified, timestamp) VALUES (?, ?, ?, ?)", (sentence_id, rating_original, rating_simplified, timestamp))
    conn.commit()
    conn.close()

init_db()
ids, sentences, simplified = load_csv()
load_sentences(ids, sentences, simplified)