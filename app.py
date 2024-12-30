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
    app.config['SITE_NAME'] = 'Flora'
    app.config['SLOGAN'] = 'Discover the World of Plants'
    app.config['SECRET_KEY'] = '724f137186bfedbee4456b0cfac7076c567a966eb0c6437c0837772e31ec21ef'

    def get_db_connection():
        try:
            conn = sqlitecloud.connect("sqlitecloud://cje5zuxinz.sqlite.cloud:8860/plantopedia.sqlite?apikey=SMZSFhzb4qCWGt8VElvtRei2kOKYWEsC1BfInDcS1RE")
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
                CREATE TABLE IF NOT EXISTS plants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    species_name TEXT NOT NULL,
                    family_name TEXT NOT NULL,
                    uses TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    approved INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            conn.close()

    create_tables()

    class PlantForm(FlaskForm):
        species_name = StringField('Species Name', validators=[DataRequired()])
        family_name = StringField('Family Name', validators=[DataRequired()])
        uses = TextAreaField('Uses', validators=[DataRequired()])
        classification = StringField('Classification', validators=[DataRequired()])

    def check_duplicate_record(species_name, family_name):
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.execute(
                    'SELECT id FROM plants WHERE species_name = ? AND family_name = ?',
                    (species_name, family_name)
                )
                record = cursor.fetchone()
                conn.close()
                return record is not None
            except Exception as e:
                print(f"Error checking duplicates: {e}")
                conn.close()
                return False
        return False

    def search_in_databases(query):
        results = []
        conn = get_db_connection()
        if conn:
            sql = 'SELECT id, species_name, family_name, uses, classification FROM plants WHERE approved = ?'
            params = [1]
            cursor = conn.execute(sql, params)
            records = cursor.fetchall()

            for row in records:
                if query.lower() in row['species_name'].lower() or query.lower() in row['family_name'].lower():
                    results.append({
                        'id': row['id'],
                        'species_name': row['species_name'],
                        'family_name': row['family_name'],
                        'uses': row['uses'],
                        'classification': row['classification']
                    })
            conn.close()

        return results

    def get_record_by_id(record_id):
        conn = get_db_connection()
        if conn:
            cursor = conn.execute(
                'SELECT id, species_name, family_name, uses, classification FROM plants WHERE id = ?',
                (record_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    'id': row['id'],
                    'species_name': row['species_name'],
                    'family_name': row['family_name'],
                    'uses': row['uses'],
                    'classification': row['classification']
                }
        return None

    def update_record_in_db(record_id, species_name, family_name, uses, classification):
        conn = get_db_connection()
        if conn:
            try:
                conn.execute(
                    'UPDATE plants SET species_name = ?, family_name = ?, uses = ?, classification = ? WHERE id = ?',
                    (species_name, family_name, uses, classification, record_id)
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
            cursor = conn.execute('SELECT id, species_name, family_name, approved FROM plants')
            records.extend([
                {'id': row['id'], 'species_name': row['species_name'], 'family_name': row['family_name'], 'approved': bool(row['approved'])}
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

        form = PlantForm()

        if form.validate_on_submit():
            species_name = form.species_name.data.strip()
            family_name = form.family_name.data.strip()
            uses = form.uses.data.strip()
            classification = form.classification.data.strip()

            if update_record_in_db(record_id, species_name, family_name, uses, classification):
                flash('Record updated successfully!', 'success')
                return redirect(url_for('home'))

        form.species_name.data = record['species_name']
        form.family_name.data = record['family_name']
        form.uses.data = record['uses']
        form.classification.data = record['classification']

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
            conn.execute('DELETE FROM plants WHERE id = ?', (record_id,))
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
            conn.execute('UPDATE plants SET approved = ? WHERE id = ?', (1, record_id))
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
                cursor = conn.execute('SELECT * FROM plants')
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