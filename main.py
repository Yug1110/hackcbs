from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

from hashlib import sha256
from pathlib import Path

import pandas as pd
import numpy as np
import tensorflow as tf

import flask
import secrets
import json
import random
import time
import pickle


class eeg_data_collection():
    def __init__(self, age=10):
        # self.age = age
        # eeg_data = eeg.collect().append(self.age)

        self.sample_eeg_data = [
                [56.0, 43.0, 278.0, 301963.0, 90612.0, 33735.0, 23991.0, 27946.0, 45097.0, 33228.0, 8293.0, 10, 0],
                [40.0, 35.0, -50.0,	73787.0, 28083.0, 1439.0, 2240.0, 2746.0, 3687.0, 5293.0, 2740.0, 10, 0],
                [47.0, 57.0, -5.0, 2012240.0, 129350.0, 61236.0, 17084.0, 11488.0, 62462.0, 49960.0, 33932.0, 10, 0]
            ]
        
        self.eeg_data = pd.DataFrame()
    

    def get_eeg(self):
        selected = pd.DataFrame(self.sample_eeg_data[random.randint(0, 2)])
        self.eeg_data = pd.concat([self.eeg_data, selected], ignore_index=True).groupby(level=0).mean()
    

    def return_eeg_data(self):
        return self.eeg_data


def encode_pass(pwd: str) -> str:
    return sha256(pwd.encode()).hexdigest()


if __name__ == '__main__':
    start = False

    saved_model = str(Path('__file__').resolve().parent) + r'\Model\Model_Data\Model.h5'
    saved_stdscaler = str(Path('__file__').resolve().parent) + r'\Model\Model_Data\StandardScaler.pkl'

    model = tf.keras.models.load_model(saved_model)

    with open(saved_stdscaler, 'rb') as f:
        sc = pickle.load(f)

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
        if 'name' not in flask.session:
            flask.session['name'] = ''
            flask.session['logged'] = False
            flask.session['test'] = False
            flask.session['id'] = None

            data_add = {
                'name': ['Samyak', 'Yugayu', 'Empty'],
                'rno': ['12345', '11111', '00000'],
                'pwd': [encode_pass('Samyak'), encode_pass('Yugayu'), encode_pass('Empty')],
                'ts': [json.dumps({'Test1': 8}), json.dumps({'Test1': 7, 'Test2': 2}), json.dumps({})]
            }

            db.drop_all()
            db.create_all()

            for i in range(len(list(data_add.values())[0])):
                db.session.add(Database(name=data_add['name'][i], rno=data_add['rno'][i], pwd=data_add['pwd'][i], ts=data_add['ts'][i]))
            db.session.commit()


    @app.route('/login/', methods=['GET', 'POST'])
    def login():
        global start

        start = False
        flask.session['test'] = False

        if flask.session['logged'] is True:
            return flask.redirect(flask.url_for('main'))
        
        if flask.request.method == 'POST':
            name = flask.request.form['name']
            rno = flask.request.form['roll']
            pwd = encode_pass(flask.request.form['password'])

            if name != '' and rno != '' and pwd != encode_pass(''):
                if Database.query.filter_by(name=name, rno=rno, pwd=pwd).all():
                    flask.session['logged'] = True
                    flask.session['name'] = name
                    flask.session['id'] = Database.query.filter_by(name=name, rno=rno, pwd=pwd).one().id

                    return flask.redirect(flask.url_for('main'))
                    
                return flask.render_template('index.html', _name=name, rno=rno, error='Invalid entry!')
            return flask.render_template('index.html', _name=name, rno=rno, error='One or more fields are empty.')

        return flask.render_template('index.html', _name='', rno='', error='')
    

    @app.route('/logout/')
    def logout():
        flask.session['logged'] = False
        flask.session['name'] = ''
        flask.session['id'] = None
        flask.session['test'] = False

        return flask.redirect(flask.url_for('main'))
    

    @app.route('/<name>/')
    def account(name):
        global start

        flask.session['test'] = False
        start = False
        if flask.session['logged'] is not False and name == flask.session['name']:
            if Database.query.get(flask.session['id']).ts == json.dumps({}):
                return flask.redirect(flask.url_for('notification', name=name))
            
            messages = {
                'Consistantly good': 'Congrats! Your are performing well!',
                'Decent': 'Your scores are decent but are below average.',
                'Bad': 'Your scores are really low, and maybe at risk of dyslexia.'
            }
            
            test_values = list(json.loads(Database.query.get(flask.session['id']).ts).values())

            avg = sum(test_values) / len(test_values)
            percent = avg * 10

            if percent >= 70:
                gm = list(messages.keys())[0]
                m = list(messages.values())[0]
            elif 30 < percent < 70:
                gm = list(messages.keys())[1]
                m = list(messages.values())[1]
            else:
                gm = list(messages.keys())[2]
                m = list(messages.values())[2]

            return flask.render_template('report.html', _value=percent, _list=test_values, gist_message=gm, test_message=m, name=name)
        return flask.redirect(flask.url_for('main'))
    

    @app.route('/<name>/notification/', methods=['GET', 'POST'])
    def notification(name):
        global start

        flask.session['test'] = False
        start = False
        if flask.session['logged'] is not False and name == flask.session['name']:
            num = len(json.loads(Database.query.get(flask.session['id']).ts)) + 1

            if flask.request.method == 'POST':
                flask.session['test'] = True
                return flask.redirect(flask.url_for('take_test', name=flask.session['name']))
            return flask.render_template('notification.html', val=num)
        
        return flask.redirect(flask.url_for('main'))
    

    @app.route('/<name>/test/', methods=['GET', 'POST'])
    def take_test(name):
        global start, sc, model, saved_stdscaler

        if flask.session['logged'] is not False and name == flask.session['name']:
            if flask.session['test'] is False:
                return flask.redirect(flask.url_for('main'))

            eeg = eeg_data_collection()
            start = True

            def eeg_func():
                global start
                while start:
                    eeg.get_eeg()
                    time.sleep(3)

            socketio.start_background_task(eeg_func)

            if flask.request.method == 'POST':
                flask.session['test'] = False
                start = False

                corr_ans = ['benny', 'forest', 'picnic', 'sandwich', 'sally']
                ans = [flask.request.form[f'ans{i}'] for i in range(1, 6)]

                scored = 0

                for i, a in enumerate(ans):
                    if corr_ans[i] in a.lower(): scored += 1

                data = eeg.return_eeg_data()

                value = np.squeeze(model.predict([sc.transform(data.to_numpy().T)])) * 30
                percent = (scored/5) * 70

                percent = round(percent + value, 2)

                data_dict = json.loads(Database.query.get(flask.session['id']).ts)
                data_dict[f'Test{len(data_dict)}'] = round(percent/10)

                data_dict = json.dumps(data_dict)
                Database.query.get(flask.session['id']).ts = data_dict
                db.session.commit()

                return flask.redirect(flask.url_for('main'))

            return flask.render_template('test.html')   
        return flask.redirect(flask.url_for('main'))
    

    @app.route('/')
    def main():
        global start

        flask.session['test'] = False
        start = False

        if flask.session['logged'] is False:
            return flask.redirect(flask.url_for('login'))
        return flask.redirect(flask.url_for('account', name=flask.session['name']))


    socketio.run(app, host='0.0.0.0', port=80, debug=True)