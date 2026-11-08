"""Read one verified chat workout as JSON on stdin and save it to the journal."""
import json
import argparse
import math
import msvcrt
import os
import shutil
import sys
import tempfile
import time
from datetime import date
from pathlib import Path


def record(workout, folder, collection='workouts'):
    # Reuse a source-based ID on retries, or an existing ID when correcting a session.
    if collection not in ('workouts', 'meals', 'energy_profiles', 'daily_energy', 'activities', 'exercise_library', 'food_options'):
        raise ValueError('Unsupported journal entry type')
    descriptions = {'workouts': ('notes',), 'meals': ('name',), 'activities': ('name',), 'exercise_library': ('name',), 'food_options': ('name','portion')}
    for field in ('id', 'source', 'date', *descriptions.get(collection, ())):
        if not isinstance(workout.get(field), str) or not workout[field].strip():
            raise ValueError(f'Missing {field}')
    date.fromisoformat(workout['date'])
    if collection in ('energy_profiles','daily_energy') and workout['id'] != workout['date']:
        raise ValueError('Use the date as the daily record ID')
    def numeric(value):
        return type(value) in (int,float) and math.isfinite(value) and value >= 0
    if collection == 'food_options' and not numeric(workout.get('kcal')):
        raise ValueError('Provide calories per serving for the saved food option')
    if collection == 'daily_energy':
        if 'weight_kg' in workout and (not numeric(workout['weight_kg']) or workout['weight_kg']==0):
            raise ValueError('Provide a positive measured weight in kilograms')
        if 'gym_attendance' in workout and workout['gym_attendance'] not in ('attended','missed'):
            raise ValueError('Gym attendance must be attended or missed')
        for field in ('full_day_burn_kcal','full_day_intake_kcal'):
            if workout.get(field) is not None and not numeric(workout[field]):
                raise ValueError(f'Invalid {field}')
        if 'intake_complete' in workout and type(workout['intake_complete']) is not bool:
            raise ValueError('intake_complete must be true or false')
        if 'training_review' in workout:
            review = workout['training_review']
            if not isinstance(review, dict) or not numeric(review.get('score')) or review['score'] > 10:
                raise ValueError('Provide a whole-day training score from 0 to 10')
            if not isinstance(review.get('note'), str) or not review['note'].strip():
                raise ValueError('Include the chat review explaining the score')
    if collection == 'energy_profiles':
        if workout.get('equation') not in ('male','female') or not all(numeric(workout.get(k)) and workout[k]>0 for k in ('kg','cm','age','pal')):
            raise ValueError('Provide the equation, weight, height, age and activity factor')
    if collection == 'activities':
        if not numeric(workout.get('minutes')) or not 0<workout['minutes']<=1440:
            raise ValueError('Provide the duration of the recorded activity')
        if not any(numeric(workout.get(k)) for k in ('total_kcal','active_kcal','met')):
            raise ValueError('Provide reported session calories or an estimated MET')
    if collection == 'meals':
        calories = workout.get('kcal')
        if calories is not None and (type(calories) not in (float, int) or not math.isfinite(calories) or calories < 0):
            raise ValueError('Calories must be a nonnegative number, or null for unknown')
        if 'estimated' in workout and type(workout['estimated']) is not bool:
            raise ValueError('estimated must be true or false')
        if 'kcal_low' in workout or 'kcal_high' in workout:
            if not all(numeric(workout.get(k)) for k in ('kcal_low','kcal','kcal_high')) or not workout['kcal_low'] <= calories <= workout['kcal_high']:
                raise ValueError('Provide a valid calorie range and midpoint')
    path = folder / 'workouts.json'
    with (folder / '.workouts.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        entries = data.setdefault(collection, [])
        if collection == 'exercise_library':
            existing = next((entry for entry in entries if entry['id'] == workout['id']), {})
            updated = {**existing, **workout}
            if updated.get('section') not in ('cardio', 'strength'):
                raise ValueError('Choose cardio or strength for this exercise')
            if updated['section'] == 'cardio' and updated.get('unit') not in ('m', 'cal', 'min', 'reps'):
                raise ValueError('Provide the unit for each cardio round')
            aliases = updated.get('aliases', [])
            if not isinstance(aliases, list) or not all(isinstance(a, str) and a.strip() for a in aliases):
                raise ValueError('Provide a list of confirmed exercise names')
            if existing and ('aliases' in workout or existing['name'] != updated['name']):
                previous_names = list(existing.get('aliases', []))
                if existing['name'] != updated['name']:
                    previous_names.append(existing['name'])
                workout = {**workout, 'aliases': list(dict.fromkeys([*previous_names, *aliases]))}
            if any(key in updated for key in ('plates_per_side_kg', 'bar_kg')):
                if not all(numeric(updated.get(key)) for key in ('plates_per_side_kg', 'bar_kg')):
                    raise ValueError('Provide the bar weight and weight on each side in kilograms')
            if 'sled_kg' in updated and (not numeric(updated['sled_kg']) or updated['sled_kg'] == 0):
                raise ValueError('Provide a positive empty sled weight in kilograms')
            def labels(entry):
                return {' '.join(n.lower().split()) for n in [entry['name'], *entry.get('aliases', [])]}
            if any(labels({**existing, **workout}) & labels(entry) for entry in entries if entry['id'] != workout['id']):
                raise ValueError('This label already identifies another exercise. Include the station or model to distinguish them.')
        for entry in entries:
            if entry['id'] == workout['id']:
                if all(entry.get(key) == value for key, value in workout.items()):
                    return 'Already saved'
                entry.update(workout)
                break
        else:
            entries.append(workout)
        backups = folder / 'backups'
        backups.mkdir(exist_ok=True)
        shutil.copy2(path, backups / f'{time.time_ns()}.json')
        with tempfile.NamedTemporaryFile(mode='w', dir=folder, delete=False, encoding='utf-8') as temp:
            json.dump(data, temp, ensure_ascii=False, indent=2)
        try:
            os.replace(temp.name, path)
        finally:
            Path(temp.name).unlink(missing_ok=True)
    return 'Saved'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    for flag, collection in (('--meal','meals'),('--activity','activities'),('--day','daily_energy'),('--profile','energy_profiles'),('--exercise','exercise_library'),('--food-option','food_options')):
        group.add_argument(flag, dest='collection', action='store_const', const=collection)
    args = parser.parse_args()
    print(record(json.load(sys.stdin), Path(__file__).resolve().parent, args.collection or 'workouts'))
