from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlitecloud
from math import ceil
import pytz
import random
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired

def create_app():
    app = Flask(__name__)
    app.config['SITE_NAME'] = 'Digo'
    app.config['SLOGAN'] = 'Search & Learn Effortlessly'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'

    connection_strings = [
        "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE",
        "sqlitecloud://cxfl3qnhhk.sqlite.cloud:8860/digo.sqlite?apikey=K0lFNDtoP9qElNFscI3UTa09ikmDvVWYCqDKw944sQo"
    ]

    conn1 = sqlitecloud.connect(connection_strings[0])
    conn2 = sqlitecloud.connect(connection_strings[1])

    def create_tables(connection):
        with connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lang TEXT NOT NULL,
                    sentence TEXT NOT NULL,
                    mean TEXT NOT NULL,
                    example TEXT NOT NULL,
                    approved INTEGER DEFAULT 0,
                    search_count INTEGER DEFAULT 0,
                    last_updated INTEGER DEFAULT 0
                )
            ''')
            cursor = connection.execute("PRAGMA table_info(records)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'last_updated' not in columns:
                connection.execute('ALTER TABLE records ADD COLUMN last_updated INTEGER DEFAULT 0')

    create_tables(conn1)
    create_tables(conn2)

    class RecordForm(FlaskForm):
        lang = StringField('Language', validators=[DataRequired()])
        sentence = TextAreaField('Sentence', validators=[DataRequired()])
        mean = TextAreaField('Meaning', validators=[DataRequired()])
        example = TextAreaField('Example', validators=[DataRequired()])

    def get_db_usage_percentage(connection_string):
        try:
            conn = sqlitecloud.connect(connection_string)
            with conn:
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA max_page_count")
                max_page_count = cursor.fetchone()[0]
                current_size = page_count * page_size
                max_size = max_page_count * page_size
                return (current_size / max_size) * 100
        except Exception as e:
            return 100

    def choose_database_for_write():
        db1_usage = get_db_usage_percentage(connection_strings[0])
        if db1_usage < 95:
            return conn1
        return conn2

    def choose_database_for_read():
        return [conn1, conn2]

    def test_connections():
        for conn in [conn1, conn2]:
            try:
                conn.execute('SELECT 1')
            except Exception:
                flash(f'Database {conn} connection failed.', 'danger')
                return False
        return True

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
        if not test_connections():
            return "Database connection error.", 500

        form = RecordForm()
        if form.validate_on_submit():
            lang = form.lang.data.strip()
            sentence = form.sentence.data.strip()
            mean = form.mean.data.strip()
            example = form.example.data.strip()
            if not (lang and sentence and mean and example):
                flash('All fields are required!', 'danger')
                return redirect(url_for('add_record'))

            if check_duplicate_record(sentence, lang):
                flash('This record already exists in the database.', 'warning')
                return redirect(url_for('home'))

            if insert_record_to_db(lang, sentence, mean, example):
                flash('Record added successfully! Awaiting approval.', 'success')
                return redirect(url_for('home'))

            flash('Failed to add record to any database.', 'danger')
            return redirect(url_for('home'))

        return render_template(
            'add_record.html',
            form=form,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
        )

    def check_duplicate_record(sentence, lang):
        for conn in choose_database_for_read():
            with conn:
                cursor = conn.execute(
                    'SELECT id FROM records WHERE sentence = ? AND lang = ?',
                    (sentence, lang)
                )
                if cursor.fetchone():
                    return True
        return False

    def insert_record_to_db(lang, sentence, mean, example):
        conn = choose_database_for_write()
        try:
            with conn:
                conn.execute(
                    'INSERT INTO records (lang, sentence, mean, example, approved, search_count) VALUES (?, ?, ?, ?, ?, ?)',
                    (lang, sentence, mean, example, 0, 0)
                )
            return True
        except Exception:
            return False

    @app.route('/search', methods=['GET'])
    def search():
        if not test_connections():
            return "Database connection error.", 500

        query = request.args.get('query', '').strip()
        page = int(request.args.get('page', 1))
        results, total_pages = [], 0

        if query:
            results = search_in_databases(query)

        items_per_page = 5
        total_items = len(results)
        total_pages = ceil(total_items / items_per_page)
        results = results[(page - 1) * items_per_page:page * items_per_page]

        if results:
            conn = choose_database_for_read()[0]
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
            current_year=datetime.now(pytz.utc).year
        )

    def search_in_databases(query):
        results = []
        for conn in choose_database_for_read():
            with conn:
                cursor = conn.execute(
                    'SELECT id, sentence, lang, mean, example, search_count FROM records WHERE approved = ?',
                    (1,)
                )
                records = cursor.fetchall()

                for row in records:
                    if query.lower() in row[1].lower():
                        results.append({
                            'id': row[0],
                            'sentence': row[1],
                            'lang': row[2],
                            'mean': row[3],
                            'example': row[4],
                            'search_count': row[5],
                        })
        return results

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

    def get_records_for_admin():
        records = []
        for conn in choose_database_for_read():
            with conn:
                cursor = conn.execute('SELECT id, lang, sentence, approved, search_count FROM records')
                records.extend([
                    {'id': row[0], 'lang': row[1], 'sentence': row[2], 'approved': bool(row[3]), 'search_count': row[4]}
                    for row in cursor.fetchall()
                ])
        return records

    @app.route('/edit/<int:record_id>', methods=['GET', 'POST'])
    def edit_record(record_id):
        if not test_connections():
            return "Database connection error.", 500

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

            if not (lang and sentence and mean and example):
                flash('All fields are required!', 'danger')
                return redirect(url_for('edit_record', record_id=record_id))

            if update_record_in_db(record_id, lang, sentence, mean, example):
                flash('Record updated successfully!', 'success')
                return redirect(url_for('home'))

            flash('Failed to update record.', 'danger')
            return redirect(url_for('home'))

        form.lang.data = record['lang']
        form.sentence.data = record['sentence']
        form.mean.data = record['mean']
        form.example.data = record['example']

        return render_template(
            'edit_record.html',
            form=form,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
        )

    def get_record_by_id(record_id):
        for conn in choose_database_for_read():
            with conn:
                cursor = conn.execute(
                    'SELECT id, lang, sentence, mean, example FROM records WHERE id = ?',
                    (record_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'lang': row[1],
                        'sentence': row[2],
                        'mean': row[3],
                        'example': row[4]
                    }
        return None

    def update_record_in_db(record_id, lang, sentence, mean, example):
        for conn in choose_database_for_read():
            try:
                with conn:
                    conn.execute(
                        'UPDATE records SET lang = ?, sentence = ?, mean = ?, example = ?, last_updated = ? WHERE id = ?',
                        (lang, sentence, mean, example, int(datetime.now(pytz.utc).timestamp()), record_id)
                    )
                return True
            except Exception:
                continue
        return False

    @app.route('/delete/<int:record_id>', methods=['POST'])
    def delete_record(record_id):
        if not test_connections():
            return "Database connection error.", 500

        for conn in choose_database_for_read():
            try:
                with conn:
                    conn.execute('DELETE FROM records WHERE id = ?', (record_id,))
                    flash('Record deleted successfully.', 'success')
                    return redirect(url_for('admin_dashboard', key='William12@OD'))
            except Exception:
                continue
        flash('Failed to delete record.', 'danger')
        return redirect(url_for('admin_dashboard', key='William12@OD'))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)