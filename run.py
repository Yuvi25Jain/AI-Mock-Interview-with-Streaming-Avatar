from app import create_app
import os, warnings
# Reduce TF logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # '0' all logs, '1' filter INFO, '2' filter WARNING, '3' filter ERROR
# Filter python warnings (be careful; this hides potentially actionable warnings)
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

app = create_app()

if __name__ == '__main__':
    # Initialize DB tables automatically on first run if needed
    with app.app_context():
        from app.db import init_db
        init_db()
        print("Database initialized.")

    app.run(debug=True, port=5000)