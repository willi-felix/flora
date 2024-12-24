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
                approved BOOLEAN DEFAULT FALSE
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                FOREIGN KEY (record_id) REFERENCES records (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,
                FOREIGN KEY (record_id) REFERENCES records (id)
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
        return render_template('add_record.html')

    @app.route('/search', methods=['GET', 'POST'])
    def search():
        query = request.args.get('query', '').strip()
        results = []
        suggestions = []
        if query:
            with conn:
                cursor = conn.execute(
                    'SELECT id, sentence, lang, mean, example FROM records WHERE (sentence LIKE ? OR mean LIKE ?) AND approved = ?',
                    (f'%{query}%', f'%{query}%', True)
                )
                results = [
                    {'id': row[0], 'sentence': row[1], 'lang': row[2], 'mean': row[3], 'example': row[4]}
                    for row in cursor.fetchall()
                ]
            if not results:
                cursor = conn.execute(
                    'SELECT sentence, mean FROM records WHERE approved = ? ORDER BY RANDOM() LIMIT 5',
                    (True,)
                )
                suggestions = [{'sentence': row[0], 'mean': row[1]} for row in cursor.fetchall()]

        current_year = datetime.now().year
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        return render_template(
            'search_results.html',
            results=results,
            suggestions=suggestions,
            query=query,
            site_name=site_name,
            slogan=slogan,
            current_year=current_year
        )

    @app.route('/rate/<int:record_id>', methods=['POST'])
    def rate_record(record_id):
        rating = request.form['rating']
        with conn:
            conn.execute(
                'INSERT INTO ratings (record_id, rating) VALUES (?, ?)',
                (record_id, rating)
            )
        flash('Thank you for your rating!')
        return redirect(request.referrer)

    @app.route('/report/<int:record_id>', methods=['POST'])
    def report_record(record_id):
        reason = request.form['reason']
        with conn:
            conn.execute(
                'INSERT INTO reports (record_id, reason) VALUES (?, ?)',
                (record_id, reason)
            )
        flash('Thank you for your report! It has been submitted.')
        return redirect(request.referrer)

    @app.route('/admincp', methods=['GET', 'POST'])
    def admin_dashboard():
        if request.args.get('key') != "William12@OD":
            return "Unauthorized Access", 403
        with conn:
            cursor = conn.execute('SELECT id, lang, sentence, approved FROM records')
            records = [
                {'id': row[0], 'lang': row[1], 'sentence': row[2], 'approved': bool(row[3])}
                for row in cursor.fetchall()
            ]
            cursor = conn.execute('SELECT record_id, COUNT(*) AS report_count FROM reports GROUP BY record_id')
            reports = [{'record_id': row[0], 'count': row[1]} for row in cursor.fetchall()]
        total_records = len(records)
        return render_template(
            'admin_dashboard.html',
            records=records,
            reports=reports,
            total_records=total_records
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)