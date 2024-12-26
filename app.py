from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlitecloud
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer, util
from math import ceil

def create_app():
    app = Flask(__name__)
    app.config['SITE_NAME'] = 'Dicgo'
    app.config['SLOGAN'] = 'Search & Learn Effortlessly'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'

    connection_string = "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE"
    conn = sqlitecloud.connect(connection_string)

    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lang TEXT NOT NULL,
                sentence TEXT NOT NULL,
                mean TEXT NOT NULL,
                example TEXT NOT NULL,
                approved INTEGER DEFAULT 0,
                search_count INTEGER DEFAULT 0
            )
        ''')
        cursor = conn.execute("PRAGMA table_info(records)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'search_count' not in columns:
            conn.execute('ALTER TABLE records ADD COLUMN search_count INTEGER DEFAULT 0')

    model = SentenceTransformer('all-MiniLM-L6-v2')

    @app.route('/')
    def home():
        return render_template(
            'home.html',
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now().year
        )

    @app.route('/add', methods=['GET', 'POST'])
    def add_record():
        if request.method == 'POST':
            lang = request.form.get('lang', '').strip()
            sentence = request.form.get('sentence', '').strip()
            mean = request.form.get('mean', '').strip()
            example = request.form.get('example', '').strip()
            if not (lang and sentence and mean and example):
                flash('All fields are required!', 'danger')
                return redirect(url_for('add_record'))
            with conn:
                conn.execute(
                    'INSERT INTO records (lang, sentence, mean, example, approved, search_count) VALUES (?, ?, ?, ?, ?, ?)',
                    (lang, sentence, mean, example, 0, 0)
                )
            flash('Record added successfully! Awaiting approval.', 'success')
            return redirect(url_for('home'))
        return render_template(
            'add_record.html',
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now().year
        )

    @app.route('/search', methods=['GET'])
    def search():
        query = request.args.get('query', '').strip()
        page = int(request.args.get('page', 1))
        results = []
        if query:
            with conn:
                cursor = conn.execute(
                    'SELECT id, sentence, lang, mean, example, search_count FROM records WHERE approved = ?',
                    (1,)
                )
                records = cursor.fetchall()

                # Convert records to embeddings and search using SentenceTransformer
                record_texts = [row[3] for row in records]  # Use the 'mean' field for matching
                record_embeddings = model.encode(record_texts, convert_to_tensor=True)
                query_embedding = model.encode(query, convert_to_tensor=True)

                similarities = util.pytorch_cos_sim(query_embedding, record_embeddings)[0]
                top_results = sorted(
                    enumerate(similarities), key=lambda x: x[1], reverse=True
                )

                for idx, score in top_results[:10]:  # Limit to top 10 results
                    if float(score) > 0.5:  # Only include results with sufficient similarity
                        row = records[idx]
                        results.append({
                            'id': row[0],
                            'sentence': row[1],
                            'lang': row[2],
                            'mean': row[3],
                            'example': row[4],
                            'search_count': row[5],
                            'score': float(score)
                        })

            items_per_page = 5
            total_items = len(results)
            total_pages = ceil(total_items / items_per_page)
            results = results[(page - 1) * items_per_page:page * items_per_page]

            if results:
                with conn:
                    conn.execute(
                        'UPDATE records SET search_count = search_count + 1 WHERE id = ?',
                        (results[0]['id'],)
                    )

        return render_template(
            'search_results.html',
            results=results,
            query=query,
            page=page,
            total_pages=total_pages,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now().year
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)