import sqlitecloud
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from math import ceil
import pytz
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired
from fuzzywuzzy import fuzz

def create_app():
    app = Flask(__name__)
    app.config['SITE_NAME'] = 'Dicgo'
    app.config['SLOGAN'] = 'Search & Learn Effortlessly'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'

    def get_db_connection():
        conn = sqlitecloud.connect(
            "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE"
        )
        conn.row_factory = sqlitecloud.Row
        return conn

    def create_tables():
        conn = get_db_connection()
        if conn:
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
            conn.commit()

    create_tables()

    class RecordForm(FlaskForm):
        lang = StringField('Language', validators=[DataRequired()])
        sentence = TextAreaField('Sentence', validators=[DataRequired()])
        mean = TextAreaField('Meaning', validators=[DataRequired()])
        example = TextAreaField('Example', validators=[DataRequired()])

    def search_in_databases(query, lang_filter=None):
        results = []
        conn = get_db_connection()
        if conn:
            cursor = conn.execute(
                'SELECT id, sentence, lang, mean, example, search_count FROM records WHERE approved = ?',
                (1,)
            )
            records = cursor.fetchall()
            for row in records:
                if lang_filter and row['lang'] != lang_filter:
                    continue
                relevance_score = fuzz.ratio(query.lower(), row['sentence'].lower())
                if relevance_score > 50:
                    results.append({
                        'id': row['id'],
                        'sentence': row['sentence'],
                        'lang': row['lang'],
                        'mean': row['mean'],
                        'example': row['example'],
                        'search_count': row['search_count'],
                        'relevance_score': relevance_score
                    })
            conn.close()
        return sorted(results, key=lambda x: x['relevance_score'], reverse=True)

    def get_languages_from_results(results):
        return sorted(list({result['lang'] for result in results}))

    def get_record_by_id(record_id):
        conn = get_db_connection()
        if conn:
            cursor = conn.execute(
                'SELECT id, lang, sentence, mean, example FROM records WHERE id = ?',
                (record_id,)
            )
            record = cursor.fetchone()
            conn.close()
            if record:
                return {
                    'id': record['id'],
                    'lang': record['lang'],
                    'sentence': record['sentence'],
                    'mean': record['mean'],
                    'example': record['example']
                }
        return None

    def update_record_in_db(record_id, lang, sentence, mean, example):
        conn = get_db_connection()
        if conn:
            conn.execute(
                'UPDATE records SET lang = ?, sentence = ?, mean = ?, example = ? WHERE id = ?',
                (lang, sentence, mean, example, record_id)
            )
            conn.commit()
            conn.close()
            return True
        return False

    def get_records_for_admin():
        conn = get_db_connection()
        if conn:
            cursor = conn.execute(
                'SELECT id, lang, sentence, approved, search_count FROM records'
            )
            records = cursor.fetchall()
            conn.close()
            return [{'id': r['id'], 'lang': r['lang'], 'sentence': r['sentence'], 'approved': r['approved'], 'search_count': r['search_count']} for r in records]
        return []

    @app.route('/')
    def home():
        return render_template(
            'home.html',
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
        )

    @app.route('/search', methods=['GET'])
    def search():
        query = request.args.get('query', '').strip()
        lang_filter = request.args.get('lang_filter', '').strip()
        page = int(request.args.get('page', 1))
        results = search_in_databases(query, lang_filter)

        items_per_page = 5
        total_items = len(results)
        total_pages = ceil(total_items / items_per_page)
        results = results[(page - 1) * items_per_page:page * items_per_page]

        languages = get_languages_from_results(results)

        return render_template(
            'search_results.html',
            results=results,
            query=query,
            page=page,
            total_pages=total_pages,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year,
            languages=languages,
            selected_lang=lang_filter
        )

    @app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
    def edit_record(record_id):
        record = get_record_by_id(record_id)
        if not record:
            flash('Record not found.', 'danger')
            return redirect(url_for('home'))

        form = RecordForm()

        if form.validate_on_submit():
            lang = form.lang.data.strip()
            sentence = form.sentence.data.strip()
            mean = form.mean.data.strip()
            example = form.example.data.strip()

            if update_record_in_db(record_id, lang, sentence, mean, example):
                flash('Record updated successfully!', 'success')
                return redirect(url_for('home'))

        form.lang.data = record['lang']
        form.sentence.data = record['sentence']
        form.mean.data = record['mean']
        form.example.data = record['example']

        return render_template(
            'edit_record.html',
            form=form,
            record=record,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN']
        )

    @app.route('/admincp', methods=['GET', 'POST'])
    def admin_dashboard():
        if request.args.get('key') != "William12@OD":
            return "Unauthorized Access", 403

        page = int(request.args.get('page', 1))
        records = get_records_for_admin()

        items_per_page = 5
        total_items = len(records)
        total_pages = ceil(total_items / items_per_page)
        records = records[(page - 1) * items_per_page:page * items_per_page]

        return render_template(
            'admin_dashboard.html',
            records=records,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN']
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)