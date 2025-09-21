#!/usr/bin/env python3
"""
Registrants Management UI - Flask Application

A comprehensive web interface for managing registrants for Chayannito 26.
Features CRUD operations, grouping by gender and group, and live verification links.
"""

import json
import os
import base64
import codecs
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = 'chayannito26-management-ui-secret-key'

# Configuration
REGISTRANTS_FILE = Path(__file__).parent / 'registrants.json'
VERIFICATION_BASE_URL = 'https://chayannito26.github.io/verify'

# Group and gender mappings
GROUP_INFO = {
    'AR': {'name': 'Arts', 'emoji': '🎨', 'color': 'blue'},
    'SC': {'name': 'Science', 'emoji': '🔬', 'color': 'red'},
    'CO': {'name': 'Commerce', 'emoji': '💼', 'color': 'green'}
}

GENDER_INFO = {
    'Male': {'short': 'B', 'color': 'blue', 'dot': '🔵'},
    'Female': {'short': 'G', 'color': 'pink', 'dot': '🟣'}
}

def load_registrants():
    """Load registrants from JSON file."""
    try:
        with open(REGISTRANTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        flash('Error reading registrants file. Using empty list.', 'error')
        return []

def save_registrants(registrants):
    """Save registrants to JSON file immediately."""
    try:
        with open(REGISTRANTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(registrants, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        flash(f'Error saving registrants: {str(e)}', 'error')
        return False

def id_to_filename(reg_id):
    """Convert registration ID to filename using the same logic as generate_verifications.py"""
    b64 = base64.urlsafe_b64encode(reg_id.encode('utf-8')).decode('utf-8')
    b64 = b64.rstrip("=")
    rot = codecs.encode(b64, "rot_13")
    return rot[::-1]

def get_verification_url(reg_id):
    """Get the verification URL for a registration ID."""
    filename = id_to_filename(reg_id)
    return f"{VERIFICATION_BASE_URL}/{filename}.html"

def get_next_registration_id(group, gender):
    """Generate the next registration ID for a group and gender."""
    registrants = load_registrants()
    gender_short = GENDER_INFO[gender]['short']
    prefix = f"{group}-{gender_short}-"
    
    # Find existing IDs with this prefix
    existing_numbers = []
    for reg in registrants:
        reg_id = reg.get('registration_id', '')
        if reg_id.startswith(prefix):
            try:
                number = int(reg_id.split('-')[-1])
                existing_numbers.append(number)
            except ValueError:
                continue
    
    # Get next number
    if existing_numbers:
        next_number = max(existing_numbers) + 1
    else:
        next_number = 1
    
    return f"{prefix}{next_number:04d}"

def group_registrants(registrants):
    """Group registrants by group and gender."""
    grouped = {}
    
    for registrant in registrants:
        reg_id = registrant.get('registration_id', '')
        if not reg_id:
            continue
            
        # Extract group from registration ID
        parts = reg_id.split('-')
        if len(parts) >= 2:
            group = parts[0]
            gender_short = parts[1]
            
            # Convert gender short to full name
            gender = None
            for g, info in GENDER_INFO.items():
                if info['short'] == gender_short:
                    gender = g
                    break
            
            if group in GROUP_INFO and gender:
                if group not in grouped:
                    grouped[group] = {}
                if gender not in grouped[group]:
                    grouped[group][gender] = []
                
                grouped[group][gender].append(registrant)
    
    return grouped

@app.route('/')
def index():
    """Main dashboard showing all registrants grouped by group and gender."""
    registrants = load_registrants()
    grouped = group_registrants(registrants)
    
    # Calculate statistics
    total_registrants = len(registrants)
    active_registrants = len([r for r in registrants if not r.get('revoked', False)])
    total_payments = sum(r.get('paid', 0) for r in registrants)
    
    stats = {
        'total': total_registrants,
        'active': active_registrants,
        'revoked': total_registrants - active_registrants,
        'total_payments': total_payments
    }
    
    return render_template('index.html', 
                         grouped=grouped, 
                         GROUP_INFO=GROUP_INFO, 
                         GENDER_INFO=GENDER_INFO,
                         stats=stats,
                         get_verification_url=get_verification_url)

@app.route('/add', methods=['GET', 'POST'])
def add_registrant():
    """Add a new registrant."""
    if request.method == 'POST':
        registrants = load_registrants()
        
        # Extract form data
        name = request.form.get('name', '').strip()
        roll = request.form.get('roll', '').strip()
        gender = request.form.get('gender', '')
        group = request.form.get('group', '')
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        paid = request.form.get('paid', 0, type=int)
        referred_by = request.form.get('referred_by', '').strip()
        parts_available = request.form.getlist('parts_available')
        
        # Validation
        if not name or not roll or not gender or not group:
            flash('Name, roll number, gender, and group are required.', 'error')
            return render_template('add_registrant.html', 
                                 GROUP_INFO=GROUP_INFO, 
                                 GENDER_INFO=GENDER_INFO,
                                 form_data=request.form)
        
        # Use provided registration_id if the user edited it, otherwise generate one
        provided_id = request.form.get('registration_id', '').strip()
        if provided_id:
            # Check uniqueness
            if any(r.get('registration_id') == provided_id for r in registrants):
                flash(f'Registration ID {provided_id} is already in use. Please choose a different ID.', 'error')
                return render_template('add_registrant.html', 
                                     GROUP_INFO=GROUP_INFO, 
                                     GENDER_INFO=GENDER_INFO,
                                     form_data=request.form)
            registration_id = provided_id
        else:
            # Generate registration ID
            registration_id = get_next_registration_id(group, gender)
        
        # Create new registrant
        new_registrant = {
            'name': name,
            'roll': roll,
            'gender': gender,
            'registration_date': datetime.now().strftime('%d %B %Y'),
            'registration_id': registration_id,
            'photo': '',
            'revoked': False,
            'referred_by': referred_by,
            'paid': paid,
            'email': email,
            'phone': phone,
            'parts_available': parts_available
        }
        
        registrants.append(new_registrant)
        
        if save_registrants(registrants):
            flash(f'Successfully added {name} with ID {registration_id}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to save registrant. Please try again.', 'error')
    
    return render_template('add_registrant.html', 
                         GROUP_INFO=GROUP_INFO, 
                         GENDER_INFO=GENDER_INFO)


@app.route('/api/next_registration_id')
def api_next_registration_id():
    """Return the next registration id for given group and gender.

    Query params: group, gender
    Response JSON: { "next_id": "AR-B-0001" }
    """
    group = request.args.get('group')
    gender = request.args.get('gender')
    if not group or not gender:
        return jsonify({'error': 'missing group or gender'}), 400
    try:
        next_id = get_next_registration_id(group, gender)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({'next_id': next_id})

@app.route('/edit/<registration_id>', methods=['GET', 'POST'])
def edit_registrant(registration_id):
    """Edit an existing registrant."""
    registrants = load_registrants()
    
    # Find the registrant
    registrant = None
    registrant_index = None
    for i, r in enumerate(registrants):
        if r.get('registration_id') == registration_id:
            registrant = r
            registrant_index = i
            break
    
    if not registrant:
        flash(f'Registrant with ID {registration_id} not found.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Update registrant data
        registrant['name'] = request.form.get('name', '').strip()
        registrant['roll'] = request.form.get('roll', '').strip()
        registrant['gender'] = request.form.get('gender', '')
        registrant['email'] = request.form.get('email', '').strip()
        registrant['phone'] = request.form.get('phone', '').strip()
        registrant['paid'] = request.form.get('paid', 0, type=int)
        registrant['referred_by'] = request.form.get('referred_by', '').strip()
        registrant['parts_available'] = request.form.getlist('parts_available')
        registrant['revoked'] = 'revoked' in request.form
        
        # Photo URL if provided
        photo_url = request.form.get('photo', '').strip()
        if photo_url:
            registrant['photo'] = photo_url
        
        registrants[registrant_index] = registrant
        
        if save_registrants(registrants):
            flash(f'Successfully updated {registrant["name"]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Failed to save changes. Please try again.', 'error')
    
    return render_template('edit_registrant.html', 
                         registrant=registrant,
                         GROUP_INFO=GROUP_INFO, 
                         GENDER_INFO=GENDER_INFO,
                         get_verification_url=get_verification_url)

@app.route('/delete/<registration_id>', methods=['POST'])
def delete_registrant(registration_id):
    """Delete a registrant."""
    registrants = load_registrants()
    
    # Find and remove the registrant
    original_count = len(registrants)
    registrants = [r for r in registrants if r.get('registration_id') != registration_id]
    
    if len(registrants) < original_count:
        if save_registrants(registrants):
            flash(f'Successfully deleted registrant with ID {registration_id}.', 'success')
        else:
            flash('Failed to delete registrant. Please try again.', 'error')
    else:
        flash(f'Registrant with ID {registration_id} not found.', 'error')
    
    return redirect(url_for('index'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for getting statistics."""
    registrants = load_registrants()
    grouped = group_registrants(registrants)
    
    stats = {
        'total': len(registrants),
        'active': len([r for r in registrants if not r.get('revoked', False)]),
        'revoked': len([r for r in registrants if r.get('revoked', False)]),
        'total_payments': sum(r.get('paid', 0) for r in registrants),
        'groups': {}
    }
    
    for group, genders in grouped.items():
        stats['groups'][group] = {
            'total': sum(len(registrants) for registrants in genders.values()),
            'genders': {gender: len(registrants) for gender, registrants in genders.items()}
        }
    
    return jsonify(stats)


@app.route('/api/student/<roll>')
def api_get_student(roll):
    """API endpoint to fetch student data by roll number.
    
    Response JSON: {
        "found": true/false,
        "student": {
            "name": "STUDENT NAME",
            "gender": "Man/Woman",
            "group": "Science/Arts/Commerce", 
            "phone": "01XXXXXXXXX"
        },
        "image_url": "/api/student-image/1202425010276"
    }
    """
    # Path to the student data file (relative to parent directory)
    students_file = Path(__file__).parent.parent / 'college-students' / 'data' / 'students.json'
    
    try:
        if not students_file.exists():
            return jsonify({
                'found': False,
                'error': 'Student data file not found',
                'image_url': '/api/student-image/placeholder'
            })
            
        with open(students_file, 'r', encoding='utf-8') as f:
            students = json.load(f)
        
        # Find student by roll number
        student = None
        for s in students:
            if str(s.get('class_roll', '')).strip() == str(roll).strip():
                student = s
                break
        
        if student:
            # Map gender values to our format
            gender_mapping = {
                'Man': 'Male',
                'Woman': 'Female',
                'Unknown': 'Male'  # Default fallback
            }
            
            # Map group values to our format
            group_mapping = {
                'Science': 'SC',
                'Arts': 'AR', 
                'Commerce': 'CO'
            }
            
            student_data = {
                'name': student.get('student_name_en', '').capitalize() if student.get('student_name_en', '') else '',
                'gender': gender_mapping.get(student.get('gender', ''), 'Male'),
                'group': group_mapping.get(student.get('group', ''), ''),
                'phone': student.get('student_phone', '')
            }
            
            return jsonify({
                'found': True,
                'student': student_data,
                'image_url': f'/api/student-image/{roll}'
            })
        else:
            return jsonify({
                'found': False,
                'error': 'Student not found',
                'image_url': '/api/student-image/placeholder'
            })
            
    except Exception as e:
        return jsonify({
            'found': False,
            'error': f'Error reading student data: {str(e)}',
            'image_url': '/api/student-image/placeholder'
        })


@app.route('/api/student-image/<roll>')
def api_student_image(roll):
    """API endpoint to serve student images.
    
    Serves images from ../college-students/images/{roll}.jpg
    Falls back to placeholder image if not found.
    """
    from flask import send_file, abort
    
    # Path to the images directory (relative to parent directory)
    images_dir = Path(__file__).parent.parent / 'college-students' / 'images'
    
    if roll == 'placeholder':
        image_path = images_dir / 'placeholder.jpg'
    else:
        image_path = images_dir / f'{roll}.jpg'
    
    # Fallback to placeholder if specific image doesn't exist
    if not image_path.exists():
        image_path = images_dir / 'placeholder.jpg'
    
    # If even placeholder doesn't exist, return 404
    if not image_path.exists():
        abort(404)
    
    return send_file(image_path, mimetype='image/jpeg')


@app.route('/push-github', methods=['POST'])
def push_github():
    """Trigger a git add/commit/push from the web UI.

    Security:
    - Requires environment variable ENABLE_GIT_PUSH=1 to be set on the server.
    - Optionally accepts a commit message in the request body as JSON or form field `message`.
    """
    # Feature toggle
    if not os.environ.get('DISABLE_GIT_PUSH', '0') != '1':
        return jsonify({'success': False, 'error': 'Git push via web is disabled on this server.'}), 403
    data = {}
    try:
        data = request.get_json(silent=True) or {}
    except Exception:
        data = {}
    # Fallback to form data
    if not data:
        data = request.form or {}

    commit_message = data.get('message') or f"Auto commit via web UI @ {datetime.utcnow().isoformat()}"

    repo_dir = Path(__file__).parent
    def run_cmd(cmd):
        try:
            if isinstance(cmd, str):
                completed = subprocess.run(cmd, cwd=repo_dir, shell=True, capture_output=True, text=True)
            else:
                completed = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
            return {
                'returncode': completed.returncode,
                'stdout': completed.stdout.strip(),
                'stderr': completed.stderr.strip()
            }
        except FileNotFoundError as e:
            return {'returncode': 127, 'stdout': '', 'stderr': str(e)}
        except Exception as e:
            return {'returncode': 1, 'stdout': '', 'stderr': str(e)}

    # Stage everything
    add_res = run_cmd(['git', 'add', '-A'])

    # Commit
    commit_res = run_cmd(['git', 'commit', '-m', commit_message])
    # If there's nothing to commit, git returns non-zero and mentions 'nothing to commit'
    commit_done = False
    if commit_res['returncode'] == 0:
        commit_done = True

    # Push
    push_res = run_cmd(['git', 'push'])

    success = (push_res.get('returncode', 1) == 0)

    response = {
        'success': success,
        'commit_done': commit_done,
        'add': add_res,
        'commit': commit_res,
        'push': push_res
    }

    status_code = 200 if success or commit_done else 500
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)