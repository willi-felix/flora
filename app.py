from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlitecloud

def create_app():
    app = Flask(__name__)
    app.config['SITE_NAME'] = 'Dicgo'
    app.config['SLOGAN'] = 'Search & Learn Effortlessly'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'

    # Kết nối SQLite Cloud
    connection_string = "sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE"
    conn = sqlitecloud.connect(connection_string)

    # Xoá các bảng không cần thiết nếu tồn tại
    with conn:
        conn.execute('DROP TABLE IF EXISTS ratings')
        conn.execute('DROP TABLE IF EXISTS reviews')
        conn.execute('DROP TABLE IF EXISTS reports')

        # Tạo bảng `records` nếu chưa tồn tại
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
                    'INSERT INTO records (lang, sentence, mean, example, approved) VALUES (?, ?, ?, ?, ?)',
                    (lang, sentence, mean, example, False)
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
        results = []
        if query:
            with conn:
                cursor = conn.execute(
                    'SELECT sentence, lang, mean, example FROM records WHERE sentence LIKE ? AND approved = ?',
                    (f'%{query}%', True)
                )
                results = [
                    {'sentence': row[0], 'lang': row[1], 'mean': row[2], 'example': row[3]}
                    for row in cursor.fetchall()
                ]
        return render_template(
            'search_results.html',
            results=results,
            query=query,
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN'],
            current_year=datetime.now().year
        )

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
        return render_template(
            'admin_dashboard.html',
            records=records,
            total_records=len(records),
            site_name=app.config['SITE_NAME'],
            slogan=app.config['SLOGAN']
        )

    @app.route('/admincp/approve/<int:record_id>', methods=['POST'])
    def approve_record(record_id):
        with conn:
            record = conn.execute('SELECT approved FROM records WHERE id = ?', (record_id,)).fetchone()
            if record and record[0] == 1:
                flash('This record has already been approved!', 'warning')
            else:
                conn.execute('UPDATE records SET approved = ? WHERE id = ?', (True, record_id))
                flash('Record approved!', 'success')
        return redirect(url_for('admin_dashboard', key="William12@OD"))

    @app.route('/admincp/delete/<int:record_id>', methods=['POST'])
    def delete_record(record_id):
        with conn:
            conn.execute('DELETE FROM records WHERE id = ?', (record_id,))
        flash('Record deleted!', 'success')
        return redirect(url_for('admin_dashboard', key="William12@OD"))

    @app.route('/admincp/edit/<int:record_id>', methods=['GET', 'POST'])
    def edit_record(record_id):
        with conn:
            record = conn.execute('SELECT * FROM records WHERE id = ?', (record_id,)).fetchone()
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