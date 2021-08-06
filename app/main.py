#!/usr/bin/env python3

import logging
from boardgamegeek import BGGClient, exceptions
from flask import Flask, render_template, redirect, session, url_for
from flask_session import Session
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from libbgg.apiv2 import BGG as BGG2
from random import randint
import ssl
from wtforms import IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, ValidationError

ssl._create_default_https_context = ssl._create_unverified_context

app = Flask(__name__)
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)

# Flask-WTF requires an encryption key - the string can be anything
app.config['SECRET_KEY'] = 'DB068F56-6044-4931-B2EB-6809FA3DD43C'

# Flask-Bootstrap requires this line
Bootstrap(app)

bgg = BGGClient()


class BGGUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    player_count = IntegerField('Minimum Player Count (Optional)', validators=[Optional()])
    submit = SubmitField('Submit')
    def validate_username(self, username):
        conn = BGG2()
        results = conn.get_user(self.username.data)
        if not results["user"]["id"]:
            raise ValidationError("Boardgamegeek username not found.")

def get_random_boardgame(username, players):
    """
    username: str > A valid boardgamegeek username
    players: int > Optional min number of players
    """
    logger = logging.getLogger("get_random_boardgame")
    collection = bgg.collection(user_name=username, own=True, exclude_subtype="boardgameexpansion")
    sub_collection = []
    try:
        if players:
            for game in collection:
                if game.min_players <= players <= game.max_players:
                    sub_collection.append(game)
            random_game = randint(0, len(sub_collection) - 1)
            return sub_collection[random_game]
        else:
            random_game = randint(0, len(collection) - 1)
            return collection[random_game]
    except ValueError:
        logger.error(
            "No boardgame found that supports %s players in  %s's library",
            players,
            username
            )
        raise

@app.route('/', methods=['GET', 'POST'])
def index():
    """Index page with form """
    form = BGGUserForm()
    message=""
    if form.validate_on_submit():
        session['username'] = form.username.data
        if form.player_count.data:
            session['player_count'] = form.player_count.data
        return redirect ( url_for('boardgame') )
    return render_template('index.html', form=form, message=message)

@app.route('/boardgame/')
def boardgame():
    """Displays the chosen boardgame"""
    try:
        game = get_random_boardgame(
                   session.get('username', None),
                   session.get('player_count', None)
                   )
    except ValueError:
        message = (f"No game found in {session.get('username', None)}'s collection "
                   f"that supports {session.get('player_count', None)} players.")
        return render_template('no-boardgame.html', message=message)
    return render_template(
        'boardgame.html',
        bg_name=game.name,
        bg_image=game.image,
        min_players=game.min_players,
        max_players=game.max_players
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
