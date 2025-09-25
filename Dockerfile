FROM python:3.12-slim
WORKDIR /app
EXPOSE 8000
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "omiver_website.wsgi:application", "--bind", "0.0.0.0:8000"]