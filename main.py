from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from hashlib import sha256

import flask
import secrets
import json


def encode_pass(pwd: str) -> str:
    return sha256(pwd.encode()).hexdigest()


if __name__ == '__main__':
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
        ts = db.Column(db.String(), unique=False, nullable=False)


    @app.before_request
    def only_once():
        global first

        if 'name' not in flask.session:
            flask.session['name'] = ''
            flask.session['logged'] = False

            data_add = {
                'name': ['Samyak', 'Yugayu'],
                'rno': ['12345', '11111'],
                'pwd': [encode_pass('Samyak'), encode_pass('Yugayu')],
                'ts': [json.dumps({}), json.dumps({})]
            }

            db.drop_all()
            db.create_all()

            for i in range(len(list(data_add.values())[0])):
                db.session.add(Database(name=data_add['name'][i], rno=data_add['rno'][i], pwd=data_add['pwd'][i], ts=data_add['ts'][i]))
            db.session.commit()


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if flask.session['logged']:
            return flask.redirect(flask.url_for('main'))
        
        if flask.request.method == 'POST':
            name = flask.request.form['name']
            rno = flask.request.form['roll']
            pwd = encode_pass(flask.request.form['password'])

            if name != '' and rno != '' and pwd != encode_pass(''):
                if Database.query.filter_by(name=name, rno=rno, pwd=pwd).all():
                    flask.session['logged'] = True
                    flask.session['name'] = name

                    return flask.redirect(flask.url_for('main'))
                    
                return flask.render_template('index.html', _name=name, rno=rno, error='Invalid entry!')
            return flask.render_template('index.html', _name=name, rno=rno, error='One or more fields are empty.')

        return flask.render_template('index.html', _name='', rno='', error='')
    

    @app.route('/<name>')
    def account(name):
        if flask.session['logged'] is not False:
            return flask.render_template('report.html')
        return flask.redirect(flask.url_for('main'))
    

    @app.route('/')
    def main():
        if flask.session['logged'] is False:
            return flask.redirect(flask.url_for('login'))
        return flask.redirect(flask.url_for('account', name=flask.session['name']))


    socketio.run(app, host='0.0.0.0', port=80, debug=True)