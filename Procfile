release: python manage.py migrate && python manage.py seed_data && python manage.py seed_roles
web: gunicorn insurance_project.wsgi --bind 0.0.0.0:$PORT