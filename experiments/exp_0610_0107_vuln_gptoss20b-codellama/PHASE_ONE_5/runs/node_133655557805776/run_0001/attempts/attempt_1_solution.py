import os
from http import HTTPStatus
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import unquote

def update_profile(request):
    # Get the current user's ID from the authentication context
    user_id = request.user.id
    
    # Extract the form data and validate it
    username = request.form['username']
    email = request.form['email']
    profile_pic = request.files['profile_pic']
    if not (3 <= len(username) <= 20):
        return {'error': 'Username must be between 3 and 20 characters long.'}, HTTPStatus.BAD_REQUEST
    elif not email or not '@' in email:
        return {'error': 'Invalid email address.'}, HTTPStatus.BAD_REQUEST
    elif profile_pic.filename == '':
        return {'error': 'No file uploaded.'}, HTTPStatus.BAD_REQUEST
    
    # Save the uploaded image to disk
    filename = f'user_{user_id}.{guess_type(profile_pic.filename)[1]}'
    profile_pic.save(os.path.join('user_profile_pics', filename))
    
    # Update the in-memory user record with the validated data
    request.user.username = username
    request.user.email = email
    
    return {'success': 'Profile updated successfully.'}, HTTPStatus.OK