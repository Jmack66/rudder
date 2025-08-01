from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
from gcode_parser import GCodeParser
from sqlalchemy.types import JSON
import threading
import time
import requests
import io
import pandas as pd
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///printer_logbook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
db = SQLAlchemy(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class PrintJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, index=True)
    gcode_path = db.Column(db.String(255), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50))  # 'success', 'failed', 'cancelled'
    quality_rating = db.Column(db.Integer)
    functionality_rating = db.Column(db.Integer)
    label = db.Column(db.String(50))
    ambient_temperature = db.Column(db.Float)
    ambient_humidity = db.Column(db.Float)
    notes = db.Column(db.Text)
    parameters = db.relationship('PrintParameters', backref='print_job', lazy=True)
    all_slicer_params = db.Column(JSON)

    # Add composite index for efficient duplicate checking
    __table_args__ = (
        db.Index('idx_filename_start_time', 'filename', 'start_time'),
    )

class PrintParameters(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    print_job_id = db.Column(db.Integer, db.ForeignKey('print_job.id'), nullable=False)
    parameter_name = db.Column(db.String(100), nullable=False)
    parameter_value = db.Column(db.String(255), nullable=False)
    is_changed = db.Column(db.Boolean, default=False)

class MaintenanceEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    todo_tasks = db.Column(db.Text)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Printer Logbook Application')
parser.add_argument('--moonraker-url', type=str,
                   help='Moonraker URL (e.g., http://192.168.1.10:7125)')
parser.add_argument('--poll-interval', type=int, default=15,
                   help='Poll interval in seconds (default: 15)')
args, unknown = parser.parse_known_args()

# Configuration priority: Command line args > Environment variables > Defaults
MOONRAKER_URL = args.moonraker_url or os.getenv('MOONRAKER_URL', 'http://192.168.1.10:7125')
POLL_INTERVAL = args.poll_interval or int(os.getenv('POLL_INTERVAL', '15'))

def poll_moonraker_for_prints():
    last_state = None
    last_filename = None
    processing_files = set()  # Track files currently being processed
    while True:
        try:
            with app.app_context():
                resp = requests.get(f'{MOONRAKER_URL}/printer/objects/query?print_stats', timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    print_stats = data.get('result', {}).get('status', {}).get('print_stats', {})
                    state = print_stats.get('state')
                    filename = print_stats.get('filename')
                    if state == 'printing' and filename:
                        # Only process if we transition to printing AND filename changed
                        if (last_state != 'printing' or last_filename != filename) and filename not in processing_files:
                            processing_files.add(filename)
                            try:
                                # Check if we already have a recent print with this filename (within last 3 minutes)
                                recent_cutoff = datetime.utcnow() - timedelta(minutes=3)
                                existing_print = PrintJob.query.filter(
                                    PrintJob.filename == filename,
                                    PrintJob.start_time >= recent_cutoff
                                ).first()

                                if existing_print:
                                    print(f"Skipping duplicate print detection for {filename} - already exists")
                                else:
                                    # Try to download the GCode file from Moonraker
                                    gcode_url = f'{MOONRAKER_URL}/server/files/gcodes/{filename}'
                                    local_path = os.path.join(app.config['UPLOAD_FOLDER'], f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}")
                                    try:
                                        file_resp = requests.get(gcode_url, timeout=10)
                                        if file_resp.status_code == 200:
                                            with open(local_path, 'wb') as f:
                                                f.write(file_resp.content)
                                            # Parse GCode parameters
                                            parser = GCodeParser()
                                            parameters = parser.parse_file(local_path)

                                            # Double-check for duplicates right before insertion
                                            final_check = PrintJob.query.filter(
                                                PrintJob.filename == filename,
                                                PrintJob.start_time >= recent_cutoff
                                            ).first()

                                            if not final_check:
                                                new_print = PrintJob(
                                                    filename=filename,
                                                    gcode_path=local_path,
                                                    start_time=datetime.utcnow(),
                                                    status=None,
                                                    all_slicer_params=parameters.get('all_slicer_params', {})
                                                )
                                                db.session.add(new_print)
                                                db.session.flush()
                                                # Add parameters
                                                for name, value in parameters.items():
                                                    if value is not None and name != 'all_slicer_params':
                                                        param = PrintParameters(
                                                            print_job_id=new_print.id,
                                                            parameter_name=name,
                                                            parameter_value=str(value)
                                                        )
                                                        db.session.add(param)
                                                db.session.commit()
                                                print(f"Added new auto-detected print: {filename}")
                                            else:
                                                print(f"Final duplicate check prevented creation of {filename}")
                                        else:
                                            # If file not found, just add basic info
                                            final_check = PrintJob.query.filter(
                                                PrintJob.filename == filename,
                                                PrintJob.start_time >= recent_cutoff
                                            ).first()

                                            if not final_check:
                                                new_print = PrintJob(
                                                    filename=filename,
                                                    gcode_path='',
                                                    start_time=datetime.utcnow(),
                                                    status=None
                                                )
                                                db.session.add(new_print)
                                                db.session.commit()
                                                print(f"Added basic print info for: {filename}")
                                            else:
                                                print(f"Prevented duplicate basic print for {filename}")
                                    except Exception as e:
                                        print(f"Moonraker GCode download/parse error: {e}")
                                        # Add print with minimal info - final duplicate check
                                        final_check = PrintJob.query.filter(
                                            PrintJob.filename == filename,
                                            PrintJob.start_time >= recent_cutoff
                                        ).first()

                                        if not final_check:
                                            new_print = PrintJob(
                                                filename=filename,
                                                gcode_path='',
                                                start_time=datetime.utcnow(),
                                                status=None
                                            )
                                            db.session.add(new_print)
                                            db.session.commit()
                                            print(f"Added minimal print info for: {filename}")
                                        else:
                                            print(f"Prevented duplicate minimal print for {filename}")
                            finally:
                                processing_files.discard(filename)
                        last_state = 'printing'
                        last_filename = filename
                    else:
                        last_state = state
                        if state != 'printing':
                            last_filename = None
        except Exception as e:
            print(f"Moonraker polling error: {e}")
        time.sleep(POLL_INTERVAL)

# Start polling in a background thread when the app starts
polling_thread = threading.Thread(target=poll_moonraker_for_prints, daemon=True)
polling_thread.start()

# Routes
@app.route('/test')
def test():
    return 'Hello, world!'

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/prints', methods=['GET'])
def get_prints():
    prints = PrintJob.query.order_by(PrintJob.start_time.desc()).all()
    return jsonify([{
        'id': p.id,
        'filename': p.filename,
        'start_time': p.start_time.isoformat(),
        'status': p.status,
        'quality_rating': p.quality_rating,
        'functionality_rating': p.functionality_rating,
        'label': p.label,
        'ambient_temperature': p.ambient_temperature,
        'ambient_humidity': p.ambient_humidity,
        'notes': p.notes,
        'parameters': [{
            'name': param.parameter_name,
            'value': param.parameter_value,
            'is_changed': param.is_changed
        } for param in p.parameters],
        'all_slicer_params': p.all_slicer_params
    } for p in prints])

@app.route('/api/prints', methods=['POST'])
def create_print():
    if 'gcode_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['gcode_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not file.filename.endswith('.gcode'):
        return jsonify({'error': 'File must be a GCode file'}), 400

    # Check for recent duplicate based on original filename (within last 10 minutes)
    recent_cutoff = datetime.utcnow() - timedelta(minutes=10)
    existing_print = PrintJob.query.filter(
        PrintJob.filename == file.filename,
        PrintJob.start_time >= recent_cutoff
    ).first()

    if existing_print:
        return jsonify({'error': f'A print with filename "{file.filename}" was already added recently'}), 409

    # Save the file
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Parse GCode parameters
    parser = GCodeParser()
    parameters = parser.parse_file(filepath)

    # Create print job with additional safeguards
    try:
        new_print = PrintJob(
            filename=file.filename,
            gcode_path=filepath,
            status='pending',
            all_slicer_params=parameters.get('all_slicer_params', {})
        )
        db.session.add(new_print)
        db.session.flush()  # Get the ID without committing

        # Add parameters
        for name, value in parameters.items():
            if value is not None and name != 'all_slicer_params':
                param = PrintParameters(
                    print_job_id=new_print.id,
                    parameter_name=name,
                    parameter_value=str(value)
                )
                db.session.add(param)

        db.session.commit()
        print(f"Added manual print: {file.filename}")
        return jsonify({'id': new_print.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating print job: {e}")
        # Check if it's a duplicate error
        existing = PrintJob.query.filter_by(filename=file.filename).first()
        if existing and (datetime.utcnow() - existing.start_time).total_seconds() < 600:
            return jsonify({'error': 'Duplicate print detected during creation'}), 409
        return jsonify({'error': 'Failed to create print job'}), 500

@app.route('/api/prints/<int:print_id>/complete', methods=['POST'])
def complete_print(print_id):
    data = request.json
    print_job = PrintJob.query.get_or_404(print_id)

    def parse_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    print_job.status = data.get('status', 'success')
    print_job.quality_rating = data.get('quality_rating')
    print_job.functionality_rating = data.get('functionality_rating')
    print_job.label = data.get('label')
    print_job.ambient_temperature = parse_float(data.get('ambient_temperature'))
    print_job.ambient_humidity = parse_float(data.get('ambient_humidity'))
    print_job.notes = data.get('notes')
    print_job.end_time = datetime.utcnow()

    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/maintenance', methods=['GET'])
def get_maintenance():
    events = MaintenanceEvent.query.order_by(MaintenanceEvent.timestamp.desc()).all()
    return jsonify([{
        'id': e.id,
        'description': e.description,
        'timestamp': e.timestamp.isoformat(),
        'todo_tasks': e.todo_tasks
    } for e in events])

@app.route('/api/maintenance', methods=['POST'])
def create_maintenance():
    data = request.json
    new_event = MaintenanceEvent(
        description=data['description'],
        todo_tasks=data.get('todo_tasks')
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify({'id': new_event.id}), 201

@app.route('/api/maintenance/<int:maintenance_id>', methods=['PUT'])
def update_maintenance(maintenance_id):
    data = request.json
    event = MaintenanceEvent.query.get_or_404(maintenance_id)

    event.description = data.get('description', event.description)
    event.todo_tasks = data.get('todo_tasks', event.todo_tasks)

    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/printer_status')
def printer_status():
    try:
        resp = requests.get(f'{MOONRAKER_URL}/printer/info', timeout=3)
        if resp.status_code == 200:
            return {'connected': True}
    except Exception:
        pass
    return {'connected': False}

@app.route('/api/export')
def export_database():
    # Query all print jobs
    prints = PrintJob.query.order_by(PrintJob.start_time.desc()).all()
    prints_data = []
    for p in prints:
        prints_data.append({
            'id': p.id,
            'filename': p.filename,
            'start_time': p.start_time.isoformat() if p.start_time else '',
            'end_time': p.end_time.isoformat() if p.end_time else '',
            'status': p.status,
            'quality_rating': p.quality_rating,
            'functionality_rating': p.functionality_rating,
            'label': p.label,
            'ambient_temperature': p.ambient_temperature,
            'ambient_humidity': p.ambient_humidity,
            'notes': p.notes,
            'parameters': str([{ 'name': param.parameter_name, 'value': param.parameter_value, 'is_changed': param.is_changed } for param in p.parameters]),
            'all_slicer_params': str(p.all_slicer_params)
        })
    prints_df = pd.DataFrame(prints_data)

    # Query all maintenance events
    events = MaintenanceEvent.query.order_by(MaintenanceEvent.timestamp.desc()).all()
    maint_data = []
    for e in events:
        maint_data.append({
            'id': e.id,
            'description': e.description,
            'timestamp': e.timestamp.isoformat() if e.timestamp else '',
            'todo_tasks': e.todo_tasks
        })
    maint_df = pd.DataFrame(maint_data)

    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        prints_df.to_excel(writer, index=False, sheet_name='PrintJobs')
        maint_df.to_excel(writer, index=False, sheet_name='Maintenance')
    output.seek(0)

    # Send as file download
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='printer_logbook_export.xlsx'
    )

@app.route('/api/debug/duplicates')
def check_duplicates():
    """Debug endpoint to check for potential duplicate prints"""
    duplicates = db.session.query(PrintJob.filename, db.func.count(PrintJob.id).label('count'))\
        .group_by(PrintJob.filename)\
        .having(db.func.count(PrintJob.id) > 1)\
        .all()

    result = []
    for filename, count in duplicates:
        prints = PrintJob.query.filter_by(filename=filename).order_by(PrintJob.start_time).all()
        result.append({
            'filename': filename,
            'count': count,
            'prints': [{
                'id': p.id,
                'start_time': p.start_time.isoformat(),
                'status': p.status,
                'gcode_path': p.gcode_path
            } for p in prints]
        })

    return jsonify({
        'duplicate_groups': result,
        'total_duplicate_groups': len(result)
    })

@app.route('/api/debug/recent_prints')
def recent_prints():
    """Debug endpoint to show recent prints for monitoring"""
    recent = PrintJob.query.order_by(PrintJob.start_time.desc()).limit(10).all()
    return jsonify([{
        'id': p.id,
        'filename': p.filename,
        'start_time': p.start_time.isoformat(),
        'status': p.status,
        'gcode_path': p.gcode_path[:50] + '...' if len(p.gcode_path) > 50 else p.gcode_path
    } for p in recent])

@app.route('/api/debug/monitor_duplicates')
def monitor_duplicates():
    """Real-time duplicate monitoring - shows prints created within last hour"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=1)

    recent_prints = PrintJob.query.filter(PrintJob.start_time >= cutoff)\
                                  .order_by(PrintJob.start_time.desc()).all()

    # Group by filename to identify potential duplicates
    by_filename = {}
    for p in recent_prints:
        if p.filename not in by_filename:
            by_filename[p.filename] = []
        by_filename[p.filename].append(p)

    suspicious = []
    for filename, prints in by_filename.items():
        if len(prints) > 1:
            suspicious.append({
                'filename': filename,
                'count': len(prints),
                'prints': [{
                    'id': p.id,
                    'start_time': p.start_time.isoformat(),
                    'status': p.status,
                    'time_diff_seconds': (prints[0].start_time - p.start_time).total_seconds() if p != prints[0] else 0
                } for p in sorted(prints, key=lambda x: x.start_time, reverse=True)]
            })

    return jsonify({
        'recent_hour_count': len(recent_prints),
        'suspicious_duplicates': suspicious,
        'total_suspicious_groups': len(suspicious)
    })

if __name__ == '__main__':
    print(f"Starting Printer Logbook with Moonraker URL: {MOONRAKER_URL}")
    print(f"Poll interval: {POLL_INTERVAL} seconds")

    with app.app_context():
        # db.drop_all() # if for whatever reason you want to drop all
        db.create_all()
    app.run(debug=True)
