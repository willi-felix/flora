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
    app.config['SITE_NAME'] = 'Digo'
    app.config['SLOGAN'] = 'Search & Learn Effortlessly'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'

    def get_db_connection():
        try:
            conn = sqlitecloud.connect(
                "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE")
            conn.row_factory = sqlitecloud.Row
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None

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
            conn.commit()
            conn.close()

    create_tables()

    class RecordForm(FlaskForm):
        lang = StringField('Language', validators=[DataRequired()])
        sentence = TextAreaField('Sentence', validators=[DataRequired()])
        mean = TextAreaField('Meaning', validators=[DataRequired()])
        example = TextAreaField('Example', validators=[DataRequired()])

    def check_duplicate_record(sentence, lang):
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.execute(
                    'SELECT id FROM records WHERE sentence = ? AND lang = ?',
                    (sentence, lang)
                )
                record = cursor.fetchone()
                conn.close()
                return record is not None
            except Exception as e:
                print(f"Error checking duplicates: {e}")
                conn.close()
                return False
        return False

    def insert_record_to_db(lang, sentence, mean, example):
        retries = 3
        for attempt in range(retries):
            conn = get_db_connection()
            if conn:
                try:
                    conn.execute(
                        'INSERT INTO records (lang, sentence, mean, example, approved, search_count) VALUES (?, ?, ?, ?, ?, ?)',
                        (lang, sentence, mean, example, 0, 0)
                    )
                    conn.commit()
                    conn.close()
                    return True
                except Exception as e:
                    print(f"Error inserting record on attempt {attempt + 1}: {e}")
                    conn.close()
                    if attempt < retries - 1:
                        continue
                    else:
                        return False
        return False

    def search_in_databases(query):
        results = []
        conn = get_db_connection()
        if conn:
            sql = 'SELECT id, sentence, lang, mean, example, search_count FROM records WHERE approved = ?'
            params = [1]

            cursor = conn.execute(sql, params)
            records = cursor.fetchall()

            for row in records:
                if len(query) == 1 and query.lower() == row['sentence'].lower():
                    results.append({
                        'id': row['id'],
                        'sentence': row['sentence'],
                        'lang': row['lang'],
                        'mean': row['mean'],
                        'example': row['example'],
                        'search_count': row['search_count'],
                        'relevance_score': 100
                    })
                elif len(query) > 1:
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

        results = sorted(results, key=lambda x: x['relevance_score'], reverse=True)
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
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error updating record: {e}")
                return False
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
            conn.commit()
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
            conn.commit()
            conn.close()
            flash('Record approved successfully.', 'success')
        except Exception as e:
            print(f"Error approving record: {e}")
            flash('Failed to approve record.', 'danger')

        return redirect(url_for('admin_dashboard', key='William12@OD'))

    @app.route('/debug_records', methods=['GET'])
    def debug_records():
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.execute('SELECT * FROM records')
                records = cursor.fetchall()
                conn.close()
                return {'records': [dict(record) for record in records]}
            except Exception as e:
                conn.close()
                return {'error': str(e)}, 500
        return {'error': 'Failed to connect to database'}, 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)