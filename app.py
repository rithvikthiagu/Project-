from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import text, func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///myapp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
app.secret_key = 'your_secret_key'  

class Users(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)

class Exercises(db.Model):
    exercise_id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(255), nullable=False)

class Routines(db.Model):
    routine_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    routine_name = db.Column(db.String(255), nullable=False)

class Workouts(db.Model):
    workout_id = db.Column(db.Integer, primary_key=True)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.routine_id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.exercise_id'), nullable=False)

class Logs(db.Model):
    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    routine_id = db.Column(db.Integer, db.ForeignKey('routines.routine_id'), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey('exercises.exercise_id'), nullable=False)
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    distance = db.Column(db.Float)
    time = db.Column(db.Float)
    date = db.Column(db.Date)
    routine = db.relationship('Routines', backref='logs', lazy=True)
    exercise = db.relationship('Exercises', backref='logs', lazy=True)

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        user = Users.query.filter_by(email=email).first()
        if user is None:
            new_user = Users(username=username, email=email)
            db.session.add(new_user)
            db.session.commit()
            user = new_user
        session['user_id'] = user.user_id
        session['previous_url'] = url_for('dashboard')
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    session['previous_url'] = url_for('dashboard')
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

@app.route('/exercises', methods=['GET', 'POST'])
def exercises():
    session['previous_url'] = url_for('exercises')
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        exercise_name = request.form.get('exercise_name')
        if exercise_name:
            try:
                db.session.begin()  # Start a transaction

                new_exercise = Exercises(exercise_name=exercise_name)
                db.session.add(new_exercise)
                db.session.commit()  # Commit the transaction

            except Exception as e:
                db.session.rollback()  # Rollback the transaction in case of an exception
                print(f"Error: {str(e)}")
            finally:
                db.session.close()

    all_exercises = Exercises.query.all()
    return render_template('exercises.html', exercises=all_exercises)

@app.route('/routines', methods=['GET', 'POST'])
def routines():
    session['previous_url'] = url_for('routines')
    if 'user_id' not in session:
        return redirect('/login')
    
    if request.method == 'POST':
        routine_name = request.form['routine_name']
        selected_exercises_ids = request.form.getlist('exercises')
        
        try:
            db.session.begin()  # Start a transaction

            new_routine = Routines(user_id=session['user_id'], routine_name=routine_name)
            db.session.add(new_routine)
            db.session.commit()  # Commit the transaction

            for exercise_id in selected_exercises_ids:
                try:
                    db.session.begin()  # Start a transaction for each workout

                    new_workout = Workouts(routine_id=new_routine.routine_id, exercise_id=exercise_id)
                    db.session.add(new_workout)
                    db.session.commit()  # Commit the transaction

                except Exception as e:
                    db.session.rollback()  # Rollback the transaction in case of an exception
                    print(f"Error: {str(e)}")
                finally:
                    db.session.close()

        except Exception as e:
            db.session.rollback()  # Rollback the transaction in case of an exception
            print(f"Error: {str(e)}")
        finally:
            db.session.close()

    exercises = Exercises.query.all()
    user_routines = Routines.query.filter_by(user_id=session['user_id']).all()
    return render_template('routines.html', routines=user_routines, exercises=exercises)

@app.route('/workout_log', methods=['GET', 'POST'])
def workout_log():
    session['previous_url'] = url_for('workout_log')
    if 'user_id' not in session:
        return redirect('/login')
    if request.method == 'POST':
        date_str = request.form.get('date')
        routine_id = request.form.get('routine')
        exercise_id = request.form.get('exercise')
        sets = request.form.get('sets')
        reps = request.form.get('reps')
        weight = request.form.get('weight')
        distance = request.form.get('distance')
        time = request.form.get('time')

        sets = None if sets == '' else sets
        reps = None if reps == '' else reps
        weight = None if weight == '' else float(weight)
        distance = None if distance == '' else float(distance)
        time = None if time == '' else float(time)

        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        new_log = Logs(
            user_id=session['user_id'],
            routine_id=routine_id,
            exercise_id=exercise_id,
            sets=sets,
            reps=reps,
            weight=weight,
            distance=distance,
            time=time,
            date=date
        )

        db.session.add(new_log)
        db.session.commit()

    log_entries = Logs.query.filter_by(user_id=session['user_id']).all()
    exercises = Exercises.query.all()
    routines = Routines.query.filter_by(user_id=session['user_id']).all()
    return render_template('workout_log.html', log_entries=log_entries, exercises=exercises, routines=routines)

@app.route('/delete_log/<int:log_id>', methods=['POST'])
def delete_log(log_id):
    log_entry = Logs.query.get(log_id)
    if log_entry and log_entry.user_id == session['user_id']:
        db.session.delete(log_entry)
        db.session.commit()
    return redirect('/workout_log')

@app.route('/edit_log/<int:log_id>', methods=['GET', 'POST'])
def edit_log(log_id):
    session['previous_url'] = url_for('workout_log')
    if 'user_id' not in session:
        return redirect('/login')

    log_entry = Logs.query.get_or_404(log_id)
    if request.method == 'POST':
        date_str = request.form.get('date')
        routine_id = request.form.get('routine')
        exercise_id = request.form.get('exercise')
        sets = request.form.get('sets')
        reps = request.form.get('reps')
        weight = request.form.get('weight')
        distance = request.form.get('distance')
        time = request.form.get('time')

        weight = None if weight == '' else float(weight)
        distance = None if distance == '' else float(distance)
        time = None if time == '' else float(time)

        log_entry.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        log_entry.routine_id = routine_id
        log_entry.exercise_id = exercise_id
        log_entry.sets = sets
        log_entry.reps = reps
        log_entry.weight = weight
        log_entry.distance = distance
        log_entry.time = time

        db.session.commit()
        return redirect('/workout_log')

    routines = Routines.query.filter_by(user_id=session['user_id']).all()
    exercises = Exercises.query.all()
    return render_template('edit_log.html', log_entry=log_entry, routines=routines, exercises=exercises)

@app.route('/workout-log-report', methods=['GET', 'POST'])
def workout_log_report():
    if request.method == 'POST':
        # Get filter criteria from the form
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        sets = request.form.get('sets')
        reps = request.form.get('reps')
        weight = request.form.get('weight')
        distance = request.form.get('distance')
        time = request.form.get('time')

        # Build the base query
        query = Logs.query

        # Apply filters
        if start_date:
            query = query.filter(Logs.date >= start_date)
        if end_date:
            query = query.filter(Logs.date <= end_date)
        if sets:
            query = query.filter(Logs.sets == sets)
        if reps:
            query = query.filter(Logs.reps == reps)
        if weight:
            query = query.filter(Logs.weight == weight)
        if distance:
            query = query.filter(Logs.distance == distance)
        if time:
            query = query.filter(Logs.time == time)
        
        # Get the filtered log entries
        filtered_logs = query.all()

        # Calculate statistics based on filtered entries
        average_sets = query.with_entities(func.avg(Logs.sets)).scalar()
        average_reps = query.with_entities(func.avg(Logs.reps)).scalar()
        average_weight = query.with_entities(func.avg(Logs.weight)).scalar()
        average_distance = query.with_entities(func.avg(Logs.distance)).scalar()
        average_time = query.with_entities(func.avg(Logs.time)).scalar()

        # Query the user's routines and exercises
        user_routines = Routines.query.filter_by(user_id=session['user_id']).all()

        # Pass the routines and exercises to the template
        return render_template('workout_report.html', filtered_logs=filtered_logs,
                               average_sets=average_sets, average_reps=average_reps,
                               average_weight=average_weight, average_distance=average_distance,
                               average_time=average_time, routines=user_routines,
                               exercises=[])

    # Default response in case no data is available
    return render_template('workout_report.html', filtered_logs=None,
                           average_sets=None, average_reps=None,
                           average_weight=None, average_distance=None,
                           average_time=None, routines=[], exercises=[])

@app.route('/go_back')
def go_back():
    return redirect(session.get('previous_url', url_for('dashboard')))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
