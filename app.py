from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlitecloud
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

    connection_string = "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE"
    conn1 = sqlitecloud.connect(connection_string)

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

    create_tables(conn1)

    class RecordForm(FlaskForm):
        lang = StringField('Language', validators=[DataRequired()])
        sentence = TextAreaField('Sentence', validators=[DataRequired()])
        mean = TextAreaField('Meaning', validators=[DataRequired()])
        example = TextAreaField('Example', validators=[DataRequired()])

    def insert_record_to_db(lang, sentence, mean, example):
        with conn1:
            conn1.execute(
                'INSERT INTO records (lang, sentence, mean, example, approved, search_count, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (lang, sentence, mean, example, 0, 0, int(datetime.now(pytz.utc).timestamp()))
            )

    def update_record_in_db(record_id, lang, sentence, mean, example):
        with conn1:
            conn1.execute(
                'UPDATE records SET lang = ?, sentence = ?, mean = ?, example = ?, last_updated = ? WHERE id = ?',
                (lang, sentence, mean, example, int(datetime.now(pytz.utc).timestamp()), record_id)
            )

    def delete_record_from_db(record_id):
        with conn1:
            conn1.execute('DELETE FROM records WHERE id = ?', (record_id,))

    def search_in_databases(query):
        results = []
        with conn1:
            cursor = conn1.execute(
                'SELECT id, sentence, lang, mean, example, search_count FROM records WHERE approved = 1 AND sentence LIKE ?',
                (f'%{query}%',)
            )
            records = cursor.fetchall()
            for row in records:
                results.append({
                    'id': row[0],
                    'sentence': row[1],
                    'lang': row[2],
                    'mean': row[3],
                    'example': row[4],
                    'search_count': row[5]
                })
        return results

    def get_record_by_id(record_id):
        with conn1:
            cursor = conn1.execute(
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

    def get_all_records():
        records = []
        with conn1:
            cursor = conn1.execute(
                'SELECT id, lang, sentence, mean, example, approved, search_count FROM records'
            )
            for row in cursor.fetchall():
                records.append({
                    'id': row[0],
                    'lang': row[1],
                    'sentence': row[2],
                    'mean': row[3],
                    'example': row[4],
                    'approved': bool(row[5]),
                    'search_count': row[6]
                })
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
            insert_record_to_db(lang, sentence, mean, example)
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
            update_record_in_db(record_id, lang, sentence, mean, example)
            flash('Record updated successfully!', 'success')
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

    @app.route('/delete/<int:record_id>', methods=['POST'])
    def delete_record(record_id):
        delete_record_from_db(record_id)
        flash('Record deleted successfully.', 'success')
        return redirect(url_for('home'))

    @app.route('/admin', methods=['GET'])
    def admin_dashboard():
        records = get_all_records()
        return render_template(
            'admin_dashboard.html',
            records=records,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now(pytz.utc).year
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)