import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lang = db.Column(db.String(50), nullable=False)
    sentence = db.Column(db.Text, nullable=False)
    mean = db.Column(db.Text, nullable=False)
    example = db.Column(db.Text, nullable=False)
    approved = db.Column(db.Boolean, default=False)

def create_app():
    app = Flask(__name__)
    app.config['SITE_NAME'] = os.getenv('SITE_NAME', 'Dicgo')
    app.config['SLOGAN'] = os.getenv('SLOGAN', 'Search & Learn Effortlessly')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLITE_CLOUD_DB_URI', 'sqlitecloud://cje5zuxinz.sqlite.cloud:8860/dicgo.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef')
    db.init_app(app)
    with app.app_context():
        db.create_all()

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
            new_record = Record(lang=lang, sentence=sentence, mean=mean, example=example, approved=False)
            db.session.add(new_record)
            db.session.commit()
            flash('Record added successfully! Awaiting approval.')
            return redirect(url_for('home'))
        return render_template('add_record.html', site_name=site_name, slogan=slogan, current_year=current_year)

    @app.route('/search', methods=['GET'])
    def search():
        query = request.args.get('query', '')
        results = Record.query.filter(Record.sentence.contains(query), Record.approved.is_(True)).all()
        current_year = datetime.now().year
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        return render_template('search_results.html', results=results, query=query, site_name=site_name, slogan=slogan, current_year=current_year)

    @app.route('/admincp', methods=['GET', 'POST'])
    def admin_dashboard():
        if request.args.get('key') != "William12@OD":
            return "Unauthorized Access", 403
        records = Record.query.all()
        total_records = len(records)
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        return render_template('admin_dashboard.html', records=records, total_records=total_records, site_name=site_name, slogan=slogan)

    @app.route('/admincp/edit/<int:record_id>', methods=['GET', 'POST'])
    def edit_record(record_id):
        record = Record.query.get(record_id)
        if not record:
            flash('Record not found!', 'danger')
            return redirect(url_for('admin_dashboard', key="William12@OD"))
        if request.method == 'POST':
            record.lang = request.form['lang']
            record.sentence = request.form['sentence']
            record.mean = request.form['mean']
            record.example = request.form['example']
            db.session.commit()
            flash('Record updated successfully!')
            return redirect(url_for('admin_dashboard', key="William12@OD"))
        site_name = app.config['SITE_NAME']
        slogan = app.config['SLOGAN']
        return render_template('edit_record.html', record=record, site_name=site_name, slogan=slogan)

    @app.route('/admincp/approve/<int:record_id>', methods=['POST'])
    def approve_record(record_id):
        record = Record.query.get(record_id)
        if record:
            record.approved = True
            db.session.commit()
            flash('Record approved!')
        return redirect(url_for('admin_dashboard', key="William12@OD"))

    @app.route('/admincp/delete/<int:record_id>', methods=['POST'])
    def delete_record(record_id):
        record = Record.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            flash('Record deleted!')
        return redirect(url_for('admin_dashboard', key="William12@OD"))

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)