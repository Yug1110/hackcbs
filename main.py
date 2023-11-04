from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from hashlib import sha256

import flask
import secrets


def encode_pass(pwd: str) -> str:
    return sha256(pwd.encode()).hexdigest()


if __name__ == '__main__':
    first = False

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SECRET_KEY'] = secrets.token_urlsafe(16)

    socketio = SocketIO(app, async_mode='threading')
    db = SQLAlchemy(app)

    class Database(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(), unique=False, nullable=False)
        rno = db.Column(db.String(), unique=True, nullable=False)
        pwd = db.Column(db.String(), unique=False, nullable=False)


    @app.before_request
    def only_once():
        global first

        if first is False:
            first = True

            flask.session['name'] = ''
            flask.session['logged'] = False

            data_add = {
                'name': ['Samyak', 'Yugayu'],
                'rno': ['12345', '11111'],
                'pwd': [encode_pass('Samyak'), encode_pass('Yugayu')]
            }

            db.drop_all()
            db.create_all()

            for i in range(len(list(data_add.values())[0])):
                db.session.add(Database(name=data_add['name'][i], rno=data_add['rno'][i], pwd=data_add['pwd'][i]))
            db.session.commit()


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if flask.session['logged']:
            return
        
        if flask.request.method == 'POST':
            name = flask.request.form['name']
            rno = flask.request.form['roll']
            pwd = encode_pass(flask.request.form['password'])

            if name != '' and rno != '' and pwd != encode_pass(''):
                if Database.query.filter_by(name=name, rno=rno, pwd=pwd).all():
                    flask.session['logged_in'] = True
                    flask.session['name'] = name

                    return
                    
                return flask.render_template('index.html', _name=name, rno=rno, error='Invalid entry!')
            return flask.render_template('index.html', _name=name, rno=rno, error='One or more fields are empty.')

        return flask.render_template('index.html', _name='', rno='', error='')
    

    @app.route('/')
    def main():
        if not flask.session['logged']:
            return flask.redirect(flask.url_for('login'))
        return


    socketio.run(app, host='0.0.0.0', port=80, debug=True)