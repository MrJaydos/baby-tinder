# Import the create app function from the website package defined by the folder.
from website import create_app

# Stores the flask app instance from the factory function so it can be referenced later.
app = create_app()

# Only runs when this file is executed direct, not when imported as a module.
if __name__ == '__main__':
    app.run(debug=True)