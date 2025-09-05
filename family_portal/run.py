from app import create_app, db, socketio
from app.models import User, Event, Expense, Photo, Message

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Event': Event,
        'Expense': Expense,
        'Photo': Photo,
        'Message': Message
    }

if __name__ == '__main__':
    socketio.run(app, debug=True)
