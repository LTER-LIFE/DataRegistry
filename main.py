from website import create_app

app = create_app()
# reminder for postgresql extend the database with postgis

# Create the flask app instance
if __name__ == '__main__':
    app.run(debug=True)