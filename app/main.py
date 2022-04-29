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
    """
    Custom form for getting BGG user input

    Attributes
    ----------
    username : str
        BoardGameGeek username from the input form
    player_count : int
        Optional minimum number of players the game should support
    playing_time : int
        Optional maximum time you have to play games
    """
    username = StringField(
        label=('Username'),
        validators=[DataRequired()])
    def validate_username(form, field):
        """ Verifies the input username is valid on boardgamegeek.com """
        conn = BGG2()
        results = conn.get_user(field.data)
        if not results["user"]["id"]:
            raise ValidationError("Boardgamegeek username not found.")
    player_count = IntegerField(
        label=('Minimum Player Count (Optional)'),
        validators=[Optional()])
    playing_time = IntegerField(
        label=('Available Playing Time [Minutes] (Optional)'),
        validators=[Optional()])
    submit = SubmitField('Submit')

def get_random_boardgame(username: str, players: int, playing_time: int):
    """ Displays a random boardgame from the specified user's collection

    Parameters
    ----------
    username : str
        A valid boardgamegeek username
    players : int
        Optional min number of players the randomly chosen game should support
    playing_time: int
        Optional maximum playtime available to play

    Returns
    -------
    game : boardgamegeek.objects.games.CollectionBoardGame
        A CollectionBoardGame object containing details about the randomly selected game
    """
    logger = logging.getLogger("get_random_boardgame")
    collection = bgg.collection(user_name=username, own=True, exclude_subtype="boardgameexpansion")
    sub_collection = []
    try:
        if players or playing_time:
            if players and playing_time:
                logger.debug(
                    "Looking for game that supports %s players under %s minutes in %s's collection",
                    players,
                    playing_time,
                    username
                    )
                for game in collection:
                    if (game.min_players <= players <= game.max_players) and \
                            (game.playing_time <= playing_time):
                        sub_collection.append(game)
            elif players:
                logger.debug(
                    "Looking for game that supports %s players in %s's collection",
                    players,
                    username
                    )
                for game in collection:
                    if game.min_players <= players <= game.max_players:
                        sub_collection.append(game)
            else:
                logger.debug(
                    "Looking for game that plays under %s minutes in %s's collection",
                    playing_time,
                    username
                    )
                for game in collection:
                    if game.playing_time <= playing_time:
                        sub_collection.append(game)
            random_game = randint(0, len(sub_collection) - 1)
            game = sub_collection[random_game]
        else:
            logger.debug("Looking for a game in %s's collection", username)
            random_game = randint(0, len(collection) - 1)
            game = collection[random_game]
        return game
    except ValueError as err:
        raise Exception(
            f"No boardgame found that supports {players} players in  {username}'s library"
        ) from err

@app.route('/', methods=['GET', 'POST'])
def index():
    """Index page with form """
    form = BGGUserForm()
    message=""
    if form.validate_on_submit():
        session['username'] = form.username.data
        if form.player_count.data:
            session['player_count'] = form.player_count.data
        if form.playing_time.data:
            session['playing_time'] = form.playing_time.data
        return redirect ( url_for('boardgame') )
    return render_template('index.html', form=form, message=message)

@app.route('/boardgame/')
def boardgame():
    """Displays the chosen boardgame"""
    try:
        game = get_random_boardgame(
                   session.get('username', None),
                   session.get('player_count', None),
                   session.get('playing_time', None)
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
        max_players=game.max_players,
        playing_time=game.playing_time,
        username=session.get('username', None)
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
