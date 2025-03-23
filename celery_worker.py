from app import create_app
from app.celery_app import celery

app = create_app()

app_context = app.app_context()
app_context.push()
