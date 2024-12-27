from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlitecloud
from math import ceil
import pytz
import random
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms.validators import DataRequired
from flask_wtf.recaptcha import RecaptchaField

def create_app():
    app = Flask(__name__)
    app.config['SITE_NAME'] = 'Digo'
    app.config['SLOGAN'] = 'Search & Learn Effortlessly'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'
    app.config['RECAPTCHA_PUBLIC_KEY'] = '6LfNmMEpAAAAAAYdf6_Tw5iPtDZjveU5aBXe5zd5'
    app.config['RECAPTCHA_PRIVATE_KEY'] = '6LfNmMEpAAAAADQgopL_LGEFx1lH1K-CX1GgLROm'

    connection_string1 = "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE"
    connection_string2 = "sqlitecloud://cxfl3qnhhk.sqlite.cloud:8860/digo.sqlite?apikey=K0lFNDtoP9qElNFscI3UTa09ikmDvVWYCqDKw944sQo"
    conn1 = sqlitecloud.connect(connection_string1)
    conn2 = sqlitecloud.connect(connection_string2)

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
        recaptcha = RecaptchaField()

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
            if not (lang and sentence and mean and example):
                flash('All fields are required!', 'danger')
                return redirect(url_for('add_record'))

            # Check for duplicate records in both databases
            duplicate_found = False
            for conn in [conn1, conn2]:
                with conn:
                    cursor = conn.execute(
                        'SELECT id FROM records WHERE sentence = ? AND lang = ?',
                        (sentence, lang)
                    )
                    if cursor.fetchone():
                        duplicate_found = True
                        break

            if duplicate_found:
                flash('This record already exists in the database.', 'warning')
                return redirect(url_for('home'))

            # Randomly select a database to insert into
            conn = random.choice([conn1, conn2])
            with conn:
                conn.execute(
                    'INSERT INTO records (lang, sentence, mean, example, approved, search_count) VALUES (?, ?, ?, ?, ?, ?)',
                    (lang, sentence, mean, example, 0, 0)
                )
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
        results = []
        if query:
            for conn in [conn1, conn2]:
                with conn:
                    cursor = conn.execute(
                        'SELECT id, sentence, lang, mean, example, search_count FROM records WHERE approved = ?',
                        (1,)
                    )
                    records = cursor.fetchall()

                    record_texts = [row[1] for row in records]

                    for idx, sentence in enumerate(record_texts):
                        if query.lower() in sentence.lower():
                            row = records[idx]
                            results.append({
                                'id': row[0],
                                'sentence': row[1],
                                'lang': row[2],
                                'mean': row[3],
                                'example': row[4],
                                'search_count': row[5],
                            })

            items_per_page = 5
            total_items = len(results)
            total_pages = ceil(total_items / items_per_page)
            results = results[(page - 1) * items_per_page:page * items_per_page]

            if results:
                conn = random.choice([conn1, conn2])
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

    @app.route('/admincp', methods=['GET', 'POST'])
    def admin_dashboard():
        if request.args.get('key') != "William12@OD":
            return "Unauthorized Access", 403
        page = int(request.args.get('page', 1))
        records = []
        for conn in [conn1, conn2]:
            with conn:
                cursor = conn.execute('SELECT id, lang, sentence, approved, search_count FROM records')
                records.extend([
                    {'id': row[0], 'lang': row[1], 'sentence': row[2], 'approved': bool(row[3]), 'search_count': row[4]}
                    for row in cursor.fetchall()
                ])
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

    @app.route('/admincp/approve/<int:record_id>', methods=['POST'])
    def approve_record(record_id):
        for conn in [conn1, conn2]:
            with conn:
                record = conn.execute('SELECT approved FROM records WHERE id = ?', (record_id,)).fetchone()
                if record:
                    if record[0] == 1:
                        flash('This record has already been approved!', 'warning')
                        break
                    else:
                        conn.execute('UPDATE records SET approved = ? WHERE id = ?', (1, record_id))
                        conn.commit()
                        flash('Record approved successfully!', 'success')
                        break
        return redirect(url_for('admin_dashboard', key="William12@OD"))

    @app.route('/admincp/delete/<int:record_id>', methods=['POST'])
    def delete_record(record_id):
        for conn in [conn1, conn2]:
            with conn:
                conn.execute('DELETE FROM records WHERE id = ?', (record_id,))
        flash('Record deleted!', 'success')
        return redirect(url_for('admin_dashboard', key="William12@OD"))

    @app.route('/admincp/edit/<int:record_id>', methods=['GET', 'POST'])
    def edit_record(record_id):
        record = None
        for conn in [conn1, conn2]:
            with conn:
                record = conn.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
                if record:
                    break
        if not record:
            flash('Record not found!', 'danger')
            return redirect(url_for('admin_dashboard', key="William12@OD"))
        if request.method == 'POST':
            lang = request.form.get('lang', '').strip()
            sentence = request.form.get('sentence', '').strip()
            mean = request.form.get('mean', '').strip()
            example = request.form.get('example', '').strip()
            if not (lang and sentence and mean and example):
                flash('All fields are required!', 'danger')
                return redirect(url_for('edit_record', record_id=record_id))
            for conn in [conn1, conn2]:
                with conn:
                    conn.execute(
                        'UPDATE records SET lang = ?, sentence = ?, mean = ?, example = ? WHERE id = ?',
                        (lang, sentence, mean, example, record_id)
                    )
            flash('Record updated successfully!', 'success')
            return redirect(url_for('admin_dashboard', key="William12@OD"))
        return render_template(
            'edit_record.html',
            record={
                'id': record[0], 'lang': record[1], 'sentence': record[2],
                'mean': record[3], 'example': record[4], 'approved': bool(record[5])
            },
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN']
        )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)