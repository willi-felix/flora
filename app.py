from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlitecloud

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
                approved BOOLEAN DEFAULT FALSE,
                reports INTEGER DEFAULT 0,
                ratings INTEGER DEFAULT 0
            )
        ''')

    @app.route('/')
    def home():
        current_year = datetime.now().year
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        return render_template('home.html', site_name=site_name, slogan=slogan, current_year=current_year)

    @app.route('/add', methods=['GET', 'POST'])
    def add_record():
        current_year = datetime.now().year
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        if request.method == 'POST':
            lang = request.form['lang']
            sentence = request.form['sentence']
            mean = request.form['mean']
            example = request.form['example']
            with conn:
                conn.execute(
                    'INSERT INTO records (lang, sentence, mean, example, approved) VALUES (?, ?, ?, ?, ?)',
                    (lang, sentence, mean, example, False)
                )
            flash('Record added successfully! Awaiting approval.')
            return redirect(url_for('home'))
        return render_template('add_record.html', site_name=site_name, slogan=slogan, current_year=current_year)

    @app.route('/search', methods=['GET', 'POST'])
    def search():
        query = request.args.get('query', '').strip()
        results = []
        similar = []
        if query:
            with conn:
                cursor = conn.execute(
                    'SELECT id, sentence, lang, mean, example, ratings FROM records WHERE sentence LIKE ? AND approved = ?',
                    (f'%{query}%', True)
                )
                results = [
                    {'id': row[0], 'sentence': row[1], 'lang': row[2], 'mean': row[3], 'example': row[4], 'ratings': row[5]}
                    for row in cursor.fetchall()
                ]
                if not results:
                    cursor = conn.execute(
                        'SELECT id, sentence, lang, mean, example FROM records WHERE approved = ? ORDER BY RANDOM() LIMIT 5',
                        (True,)
                    )
                    similar = [
                        {'id': row[0], 'sentence': row[1], 'lang': row[2], 'mean': row[3], 'example': row[4]}
                        for row in cursor.fetchall()
                    ]
        current_year = datetime.now().year
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        return render_template(
            'search_results.html',
            results=results,
            query=query,
            similar=similar,
            site_name=site_name,
            slogan=slogan,
            current_year=current_year
        )

    @app.route('/rate/<int:record_id>', methods=['POST'])
    def rate_record(record_id):
        with conn:
            conn.execute('UPDATE records SET ratings = ratings + 1 WHERE id = ?', (record_id,))
        flash('Thank you for your rating!')
        return redirect(url_for('search', query=request.form.get('query', '')))

    @app.route('/report/<int:record_id>', methods=['POST'])
    def report_record(record_id):
        with conn:
            conn.execute('UPDATE records SET reports = reports + 1 WHERE id = ?', (record_id,))
        flash('Report submitted. Thank you for your feedback.')
        return redirect(url_for('search', query=request.form.get('query', '')))

    @app.route('/admincp', methods=['GET', 'POST'])
    def admin_dashboard():
        if request.args.get('key') != "William12@OD":
            return "Unauthorized Access", 403
        with conn:
            cursor = conn.execute('SELECT id, lang, sentence, approved, reports FROM records')
            records = [
                {'id': row[0], 'lang': row[1], 'sentence': row[2], 'approved': bool(row[3]), 'reports': row[4]}
                for row in cursor.fetchall()
            ]
        total_records = len(records)
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        return render_template(
            'admin_dashboard.html',
            records=records,
            total_records=total_records,
            site_name=site_name,
            slogan=slogan
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)