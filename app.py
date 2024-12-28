from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import libsql_experimental as libsql
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

    connection_string = "libsql://digo-minyoongi.aws-us-west-2.turso.io?auth_token=eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3MzUzNjk5NDcsImlkIjoiMzExN2U2YjItODMyMi00ZmY2LThjNjMtOGNiODI0ZmQ1MTMzIn0.-WQhTc4cwZORMh0kPyVXEw99IM0vxWB_LTCgyBopsrV5MXQVQve8DsPwjoPu7hoH3QJ6MY5osR6g91FKHTShAA"
    conn1 = libsql.connect(connection_string)

    def create_tables(connection):
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

    class RecordForm(FlaskForm):
        lang = StringField('Language', validators=[DataRequired()])
        sentence = TextAreaField('Sentence', validators=[DataRequired()])
        mean = TextAreaField('Meaning', validators=[DataRequired()])
        example = TextAreaField('Example', validators=[DataRequired()])

    def test_connections():
        try:
            conn1.execute('SELECT 1')
            return True
        except Exception:
            return False

    def check_duplicate_record(sentence, lang):
        cursor = conn1.execute(
            'SELECT id FROM records WHERE sentence = ? AND lang = ?',
            (sentence, lang)
        )
        return cursor.fetchone() is not None

    def insert_record_to_db(lang, sentence, mean, example):
        retries = 3
        for attempt in range(retries):
            try:
                conn1.execute(
                    'INSERT INTO records (lang, sentence, mean, example, approved, search_count) VALUES (?, ?, ?, ?, ?, ?)',
                    (lang, sentence, mean, example, 0, 0)
                )
                return True
            except Exception:
                if attempt < retries - 1:
                    continue
                else:
                    return False
        return False

    def search_in_databases(query):
        results = []
        cursor = conn1.execute(
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

    def get_record_by_id(record_id):
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

    def update_record_in_db(record_id, lang, sentence, mean, example):
        try:
            conn1.execute(
                'UPDATE records SET lang = ?, sentence = ?, mean = ?, example = ?, last_updated = ? WHERE id = ?',
                (lang, sentence, mean, example, int(datetime.now(pytz.utc).timestamp()), record_id)
            )
            return True
        except Exception:
            return False

    def get_records_for_admin():
        records = []
        cursor = conn1.execute('SELECT id, lang, sentence, approved, search_count FROM records')
        records.extend([
            {'id': row[0], 'lang': row[1], 'sentence': row[2], 'approved': bool(row[3]), 'search_count': row[4]}
            for row in cursor.fetchall()
        ])
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
        if not test_connections():
            return "Database connection error.", 500

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
        if not test_connections():
            return "Database connection error.", 500

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
        if not test_connections():
            return "Database connection error.", 500

        try:
            conn1.execute('DELETE FROM records WHERE id = ?', (record_id,))
            flash('Record deleted successfully.', 'success')
            return redirect(url_for('admin_dashboard', key='William12@OD'))
        except Exception:
            flash('Failed to delete record.', 'danger')
            return redirect(url_for('admin_dashboard', key='William12@OD'))

    @app.route('/approve/<int:record_id>', methods=['POST'])
    def approve_record(record_id):
        if not test_connections():
            return "Database connection error.", 500

        try:
            conn1.execute('UPDATE records SET approved = ? WHERE id = ?', (1, record_id))
            flash('Record approved successfully.', 'success')
        except Exception:
            flash('Failed to approve record.', 'danger')

        return redirect(url_for('admin_dashboard', key='William12@OD'))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)