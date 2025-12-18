"""
ChatAI Integration Entry Point

Runs the Flask application.

Author: Konstantin Soballa
"""

from app import create_app, db

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
