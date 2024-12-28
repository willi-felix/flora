import sqlitecloud
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from math import ceil
import pytz
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired

def create_app():
    app = Flask(__name__)
    app.config['SITE_NAME'] = 'Digo'
    app.config['SLOGAN'] = 'Search & Learn Effortlessly'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'

    db_url = "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE"

    def get_db_connection(retries=3):
        attempt = 0
        while attempt < retries:
            try:
                conn = sqlitecloud.connect(db_url)
                return conn
            except Exception:
                attempt += 1
        return None

    def ensure_table_columns():
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('PRAGMA table_info(records);')
            existing_columns = [column[1] for column in cursor.fetchall()]
            conn.close()

    def create_tables():
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            conn.close()
            ensure_table_columns()

    create_tables()

    class RecordForm(FlaskForm):
        lang = StringField('Language', validators=[DataRequired()])
        sentence = TextAreaField('Sentence', validators=[DataRequired()])
        mean = TextAreaField('Meaning', validators=[DataRequired()])
        example = TextAreaField('Example', validators=[DataRequired()])

    def check_duplicate_record(sentence, lang):
        conn = get_db_connection()
        if conn:
            cursor = conn.execute(
                'SELECT id FROM records WHERE sentence = ? AND lang = ?',
                (sentence, lang)
            )
            result = cursor.fetchone()
            conn.close()
            return result is not None
        return False

    def insert_record_to_db(lang, sentence, mean, example):
        conn = get_db_connection()
        if conn:
            try:
                conn.execute(
                    'INSERT INTO records (lang, sentence, mean, example, approved, search_count) VALUES (?, ?, ?, ?, ?, ?)',
                    (lang, sentence, mean, example, 0, 0)
                )
                conn.close()
                return True
            except Exception:
                conn.close()
        return False

    def search_in_databases(query):
        results = []
        conn = get_db_connection()
        if conn:
            cursor = conn.execute(
                'SELECT id, sentence, lang, mean, example, search_count FROM records WHERE approved = ?',
                (1,)
            )
            records = cursor.fetchall()
            for row in records:
                if query.lower() in row['sentence'].lower():
                    results.append({
                        'id': row['id'],
                        'sentence': row['sentence'],
                        'lang': row['lang'],
                        'mean': row['mean'],
                        'example': row['example'],
                        'search_count': row['search_count'],
                    })
            conn.close()
        return results

    def get_record_by_id(record_id):
        conn = get_db_connection()
        if conn:
            cursor = conn.execute(
                'SELECT id, lang, sentence, mean, example FROM records WHERE id = ?',
                (record_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'id': row['id'],
                    'lang': row['lang'],
                    'sentence': row['sentence'],
                    'mean': row['mean'],
                    'example': row['example']
                }
        return None

    def update_record_in_db(record_id, lang, sentence, mean, example):
        conn = get_db_connection()
        if conn:
            try:
                conn.execute(
                    'UPDATE records SET lang = ?, sentence = ?, mean = ?, example = ? WHERE id = ?',
                    (lang, sentence, mean, example, record_id)
                )
                conn.close()
                return True
            except Exception:
                conn.close()
        return False

    def get_records_for_admin():
        records = []
        conn = get_db_connection()
        if conn:
            cursor = conn.execute('SELECT id, lang, sentence, approved, search_count FROM records')
            records.extend([
                {'id': row['id'], 'lang': row['lang'], 'sentence': row['sentence'], 'approved': bool(row['approved']), 'search_count': row['search_count']}
                for row in cursor.fetchall()
            ])
            conn.close()
        return records

    @app.route('/')
    def home():
        return render_template(
            'home.html',
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
        )

    @app.route('/add', methods=['GET', 'POST'])
    def add_record():
        form = RecordForm()
        if form.validate_on_submit():
            lang = form.lang.data.strip()
            sentence = form.sentence.data.strip()
            mean = form.mean.data.strip()
            example = form.example.data.strip()

            if check_duplicate_record(sentence, lang):
                flash('This record already exists in the database.', 'warning')
                return redirect(url_for('home'))

            if insert_record_to_db(lang, sentence, mean, example):
                flash('Record added successfully! Awaiting approval.', 'success')
                return redirect(url_for('home'))

        return render_template(
            'add_record.html',
            form=form,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
        )

    @app.route('/search', methods=['GET'])
    def search():
        query = request.args.get('query', '').strip()
        page = int(request.args.get('page', 1))
        results = search_in_databases(query)

        items_per_page = 5
        total_items = len(results)
        total_pages = ceil(total_items / items_per_page)
        results = results[(page - 1) * items_per_page:page * items_per_page]

        return render_template(
            'search_results.html',
            results=results,
            query=query,
            page=page,
            total_pages=total_pages,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
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
            total_records=total_items,
            total_pages=total_pages,
            page=page,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN']
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
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
        )

    @app.route('/delete/<int:record_id>', methods=['POST'])
    def delete_record(record_id):
        try:
            conn = get_db_connection()
            conn.execute('DELETE FROM records WHERE id = ?', (record_id,))
            conn.close()
            flash('Record deleted successfully.', 'success')
            return redirect(url_for('admin_dashboard', key='William12@OD'))
        except Exception:
            flash('Failed to delete record.', 'danger')
            return redirect(url_for('admin_dashboard', key='William12@OD'))

    @app.route('/approve/<int:record_id>', methods=['POST'])
    def approve_record(record_id):
        try:
            conn = get_db_connection()
            conn.execute('UPDATE records SET approved = ? WHERE id = ?', (1, record_id))
            conn.close()
            flash('Record approved successfully.', 'success')
        except Exception:
            flash('Failed to approve record.', 'danger')

        return redirect(url_for('admin_dashboard', key='William12@OD'))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)