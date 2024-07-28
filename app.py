from flask import Flask, request, jsonify, render_template, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_current_user, get_jwt_identity
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, date
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get('SECRET_KEY')

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)


    
# Defining models
class GameWeek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_week = db.Column(db.Integer, nullable=False, default=1)

    @staticmethod
    def get_current_week():
        game_week = GameWeek.query.first()
        if game_week:
            return game_week.current_week
        else:
            new_game_week = GameWeek(current_week=1)
            db.session.add(new_game_week)
            db.session.commit()
            return new_game_week.current_week

    @staticmethod
    def increment_week():
        game_week = GameWeek.query.first()
        if game_week:
            game_week.current_week += 1
            db.session.commit()
        else:
            new_game_week = GameWeek(current_week=2)
            db.session.add(new_game_week)
            db.session.commit()



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    favteam = db.Column(db.String(50), nullable=False)
    
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

player_teams = db.Table('player_teams',
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('team.id'), primary_key=True)
)

class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="teams")
    team_name = db.Column(db.String(50), nullable=False)
    total_points = db.Column(db.Integer, default=0)
    players = db.relationship('Player', secondary=player_teams, backref=db.backref('teams', lazy=True))
    budget = db.Column(db.Integer, default=100)
    captain_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)
    captain = db.relationship('Player', foreign_keys=[captain_id])
    
    @property
    def current_points(self):
        try:
            if not self.players:
                return 0
            else:
                points = 0
                for player in self.players:
                    if player.id == self.captain_id:
                        points += player.current_points * 3
                    else:
                        points += player.current_points
                return points
        except:
            return 0

    def add_total_points(self):
        self.total_points += self.current_points
        db.session.commit()
    
    @property
    def remaining_budget(self):
        return 100 - sum(player.price for player in self.players)
    
    def set_captain(self, player_id):
        if player_id in [player.id for player in self.players]:
            self.captain_id = player_id
            db.session.commit()

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(20), nullable=False)
    price = db.Column(db.DECIMAL(10, 2), nullable=False)
    SwepLeagueTeam_id = db.Column(db.Integer, db.ForeignKey('swep_league_team.id'), nullable=False)
    current_points = db.Column(db.Integer, default=0)
    total_points = db.Column(db.Integer, default=0)
    
    def reset_current_points(self):
        self.total_points += self.current_points
        self.current_points = 0
        db.session.commit()
        

match_saves = db.Table('match_saves',
    db.Column('match_id', db.Integer, db.ForeignKey('match.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('count', db.Integer, default=1)
)

match_goals = db.Table('match_goals',
    db.Column('match_id', db.Integer, db.ForeignKey('match.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('count', db.Integer, default=1)
)

match_assists = db.Table('match_assists',
    db.Column('match_id', db.Integer, db.ForeignKey('match.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('count', db.Integer, default=1)
)

match_yellow_cards = db.Table('match_yellow_cards',
    db.Column('match_id', db.Integer, db.ForeignKey('match.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True)
)

match_red_cards = db.Table('match_red_cards',
    db.Column('match_id', db.Integer, db.ForeignKey('match.id'), primary_key=True),
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True)
)

class Fixture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_week = db.Column(db.Integer, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('swep_league_team.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('swep_league_team.id'), nullable=False)
    kickoff_time = db.Column(db.Date, nullable=False)
    
    home_team = db.relationship('SwepLeagueTeam', foreign_keys=[home_team_id], backref='home_fixtures')
    away_team = db.relationship('SwepLeagueTeam', foreign_keys=[away_team_id], backref='away_fixtures')

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fixture_id = db.Column(db.Integer, db.ForeignKey('fixture.id'), nullable=False)
    game_week = db.Column(db.Integer, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey('swep_league_team.id'), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey('swep_league_team.id'), nullable=False)
    kickoff_time = db.Column(db.Date, nullable=False)
    home_score = db.Column(db.Integer, default=0, nullable=False)
    away_score = db.Column(db.Integer, default=0, nullable=False)
    
    home_team = db.relationship('SwepLeagueTeam', foreign_keys=[home_team_id], backref=db.backref('home_matches', lazy='dynamic'))
    away_team = db.relationship('SwepLeagueTeam', foreign_keys=[away_team_id], backref=db.backref('away_matches', lazy='dynamic'))
    
    fixture = db.relationship('Fixture', backref=db.backref('matches', lazy=True))
                        
    saves = db.relationship('Player', secondary=match_saves, backref=db.backref('saves_in_matches', lazy='dynamic'))
    goals = db.relationship('Player', secondary=match_goals, backref=db.backref('goals_in_matches', lazy='dynamic'))
    assists = db.relationship('Player', secondary=match_assists, backref=db.backref('assists_in_matches', lazy='dynamic'))
    yellow_cards = db.relationship('Player', secondary=match_yellow_cards, backref=db.backref('yellow_cards_in_matches', lazy='dynamic'))
    red_cards = db.relationship('Player', secondary=match_red_cards, backref=db.backref('red_cards_in_matches', lazy='dynamic'))
    
    __mapper_args__ = {
        'polymorphic_identity': 'match',
    }

    def get_player_stat(self, stat_type, team_id):
        if stat_type in ['saves', 'goals', 'assists']:
            return db.session.query(Player, getattr(Match, stat_type).prop.secondary.c.count).\
                join(getattr(Match, stat_type).prop.secondary).\
                filter(getattr(Match, stat_type).prop.secondary.c.match_id == self.id).\
                filter(Player.SwepLeagueTeam_id == team_id).all()
        else:
            return [(player, 1) for player in getattr(self, stat_type) if player.SwepLeagueTeam_id == team_id]

    @property
    def home_stats(self):
        return {
            'saves': self.get_player_stat('saves', self.home_team_id),
            'goals': self.get_player_stat('goals', self.home_team_id),
            'assists': self.get_player_stat('assists', self.home_team_id),
            'yellow_cards': self.get_player_stat('yellow_cards', self.home_team_id),
            'red_cards': self.get_player_stat('red_cards', self.home_team_id)
        }

    @property
    def away_stats(self):
        return {
            'saves': self.get_player_stat('saves', self.away_team_id),
            'goals': self.get_player_stat('goals', self.away_team_id),
            'assists': self.get_player_stat('assists', self.away_team_id),
            'yellow_cards': self.get_player_stat('yellow_cards', self.away_team_id),
            'red_cards': self.get_player_stat('red_cards', self.away_team_id)
        }

    @property
    def home_stats_count(self):
        return {
            'saves': sum(count for _, count in self.home_stats['saves']),
            'goals': sum(count for _, count in self.home_stats['goals']),
            'assists': sum(count for _, count in self.home_stats['assists']),
            'yellow_cards': len(self.home_stats['yellow_cards']),
            'red_cards': len(self.home_stats['red_cards'])
        }

    @property
    def away_stats_count(self):
        return {
            'saves': sum(count for _, count in self.away_stats['saves']),
            'goals': sum(count for _, count in self.away_stats['goals']),
            'assists': sum(count for _, count in self.away_stats['assists']),
            'yellow_cards': len(self.away_stats['yellow_cards']),
            'red_cards': len(self.away_stats['red_cards'])
        }
            
class UserChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref="user_challenges")
    challenge_gameweek = db.Column(db.Integer, nullable=False)
    predictions = db.relationship("UserPrediction", backref="challenge", cascade="all, delete-orphan")

class UserPrediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey("user_challenge.id"), nullable=False)
    fixture_id = db.Column(db.Integer, db.ForeignKey("fixture.id"), nullable=False)
    prediction = db.Column(db.String(10), nullable=False)
    fixture = db.relationship("Fixture", backref="predictions")


player_swepteams = db.Table('player_swepteams',
    db.Column('player_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('team_id', db.Integer, db.ForeignKey('swep_league_team.id'), primary_key=True),
)


class SwepLeagueTeam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String(20), nullable=False)
    players = db.relationship('Player', backref='swep_league_team', lazy='dynamic')    
        
    @hybrid_property
    def matches_played(self):
        return self.home_matches.count() + self.away_matches.count()
    
    @hybrid_property
    def wins(self):
        home_matches = Match.query.filter_by(home_team_id = self.id).all()
        away_matches = Match.query.filter_by(away_team_id = self.id).all()
        count = 0
        for match in home_matches:
            if match and match.home_score > match.away_score:
                count += 1
        for match in away_matches:
            if match and  match.home_score < match.away_score:
                count +=1
        return count
    
    @hybrid_property
    def draws(self):
        home_matches = Match.query.filter_by(home_team_id = self.id).all()
        away_matches = Match.query.filter_by(away_team_id = self.id).all()
        count = 0
        for match in home_matches:
            if match and match.home_score == match.away_score:
                count += 1
        for match in away_matches:
            if match and  match.home_score == match.away_score:
                count +=1
        return count
    
    @hybrid_property
    def losses(self):
        home_matches = Match.query.filter_by(home_team_id = self.id).all()
        away_matches = Match.query.filter_by(away_team_id = self.id).all()
        count = 0
        for match in home_matches:
            if match and match.home_score < match.away_score:
                count += 1
        for match in away_matches:
            if match and  match.home_score > match.away_score:
                count +=1
        return count
    
    @hybrid_property
    def goals_for(self):
        home_matches = Match.query.filter_by(home_team_id = self.id).all()
        away_matches = Match.query.filter_by(away_team_id = self.id).all()
        count = 0
        for match in home_matches:
            if match :
                count += match.home_score
        for match in away_matches:
            if match :
                count += match.away_score
        return count
    
    @hybrid_property
    def goals_against(self):
        home_matches = Match.query.filter_by(home_team_id = self.id).all()
        away_matches = Match.query.filter_by(away_team_id = self.id).all()
        count = 0
        for match in home_matches:
            if match :
                count += match.away_score
        for match in away_matches:
            if match :
                count += match.home_score
        return count
    
    @hybrid_property
    def goal_diff(self):
        return self.goals_for - self.goals_against
    
    @hybrid_property
    def total_points(self):
        return 3 * self.wins + self.draws

# Defining schemas
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True

class TeamSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Team
        load_instance = True

class PlayerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Player
        load_instance = True

class FixtureSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Fixture
        load_instance = True
        
    home_team = ma.Nested('SwepLeagueTeamSchema', only=['id', 'team_name'])
    away_team = ma.Nested('SwepLeagueTeamSchema', only=['id', 'team_name'])

class MatchSchema(FixtureSchema):
    class Meta:
        model = Match
        load_instance = True


class UserChallengeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = UserChallenge
        load_instance = True
        
class SwepLeagueTeamSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = SwepLeagueTeam
        load_instance = True
    matches_played = ma.Integer(dump_only=True)
    wins = ma.Integer(dump_only=True)
    draws = ma.Integer(dump_only=True)
    losses = ma.Integer(dump_only=True)
    goals_for = ma.Integer(dump_only=True)
    goals_against = ma.Integer(dump_only=True)
    goal_diff = ma.Integer(dump_only=True)
    total_points = ma.Integer(dump_only=True)



# Defining API endpoints

@app.route("/", methods=["GET"])
def start():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    if not user :
        return render_template("sign_in.html")
    else:
        return redirect("/fixtures")
    
@app.route("/signup", methods=["GET"])
def signup_page():
    return render_template("sign_up.html")

@app.route("/register", methods=["POST"])
def register_user():
    data = None
    
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    if not data:
        return render_template("error_signup.html", message ="Invalid JSON or form data"), 400

    required_fields = ["username", "email", "password", "team_name", "favteam"]
    for field in required_fields:
        if not data.get(field):
            return render_template("error_signup.html", message ="{field} is required"), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    team_name = data.get("team_name")
    favteam = data.get("favteam")

    
    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return render_template("error_signup.html", message ="Username or email already exists"), 400

    try:
        user = User(username=username, email=email, favteam=favteam)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        team = Team(user_id=user.id, team_name=team_name)
        db.session.add(team)
        db.session.commit()

        access_token = create_access_token(identity=username)

        response = jsonify({'access_token': access_token})
        response.status_code = 200
        response.headers['Authorization'] = f'Bearer {access_token}'

        session['user_id'] = user.id
        
        return redirect("/pickteam")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating user: {e}")
        return render_template("error_signup.html", message ="Error creating user"), 500


@app.route("/login", methods=["POST"])
def login_user():
    data = None
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()  
        
    if not data:     
        return render_template("error_signin.html", message="Invalid request"), 400
    
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return render_template("error_signin.html", message="Invalid request"), 400
    
    try:
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return render_template("error_signin.html", message="Invalid credentials"), 401
        
        team = Team.query.filter_by(user_id=user.id).first()
        if not team:
            return render_template("error_signin.html", message="Team not found"), 404

        session['user_id'] = user.id

        if len(team.players) < 15:
            return redirect("/pickteam")
        else:
            return redirect("/fixtures")
    except Exception as e:
        return render_template("error_signin.html", message=f"{e}"), 500
    
@app.route("/pickteam" , methods=["GET"])
def pickplayers():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    if not user:
        return redirect("/")
    team = Team.query.filter_by(user_id = user.id).first()
    if len(team.players) == 15:
        return redirect("/fixtures")
    players = Player.query.all()
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id : team.team_name for team in swepteam}
    return render_template("pickteam.html", teamnames = teamdict, players=players)
        
    

@app.route("/checkpickedteam", methods=["GET", "POST"])
def check_and_submit_teams():
    try:
        current_user = session.get("user_id")
        user = User.query.filter_by(id=current_user).first()
        data = request.get_json()
        players = data.get('players', [])
        
        if len(players) == 0:
            return jsonify({'error': "No players selected"}), 400
        
        seen_id = set()
        total_price = 0
        max_price = 0
        captain = None
        for player in players:
            name = player.get('name')
            playerdb = Player.query.filter_by(name=name).first()
            
            if not playerdb:
                return jsonify({'error': f"Player '{name}' not found in database"}), 404
            if playerdb.id in seen_id:
                return jsonify({'error': f"Player '{name}' is repeated"}), 400
            if playerdb.price > max_price:
                max_price = playerdb.price
                captain = playerdb
            seen_id.add(playerdb.id)
            total_price += playerdb.price


        if total_price > 100:
            return jsonify({'error': f"Total price exceeds budget (100): {total_price}"}), 400
        
        team = Team.query.filter_by(user_id=user.id).first()
        if not team:
            team = Team(user_id=user.id, team_name="Default Team Name")
            db.session.add(team)
        
        team.players = [Player.query.filter_by(id =player_id).first() for player_id in seen_id]
        team.captain = captain
        team.captain_id = captain.id
        db.session.commit()  
        return jsonify({'success': 'Succesfully picked'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@app.route("/fixtures", methods=["GET"])
def fixtures_and_matches():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    if not user:
        return redirect("/")
    fixtures = Fixture.query.all()
    fixture_schema = FixtureSchema(many=True)
    fixtures_data = fixture_schema.dump(fixtures)
    
    matches = Match.query.all()    
    matches.reverse()
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id : team.team_name for team in swepteam}
    gameweek = GameWeek.get_current_week()

    return render_template("Fixtures.html", fixtures=fixtures_data, matches=matches, matchday=gameweek, user=user, teamnames = teamdict)

@app.route("/match_details", methods=["Get", "Post"])
def show_stats():
    home_name = request.args.get("home")
    away_name = request.args.get("away")
    if not home_name or not away_name:
        return "Home team or away team not specified", 400

    home_team = SwepLeagueTeam.query.filter_by(team_name=home_name).first()
    away_team = SwepLeagueTeam.query.filter_by(team_name=away_name).first()

    if home_team is None or away_team is None:
        return "One or both teams not found", 404

    match = Match.query.filter_by(home_team_id = home_team.id, away_team_id = away_team.id).first()
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id : team.team_name for team in swepteam}
    return render_template("match.html", match = match, teamnames = teamdict)



@app.route("/tables" , methods=["GET"])
def show_all_stats():
    swepteams = SwepLeagueTeam.query.all()
    swepteams.sort(key=lambda team: team.total_points, reverse=True)
    fslteams = Team.query.all()
    teams_data_unsorted = [
        {
            "team_name": team.team_name,
            "total_points": team.total_points,
            "current_points": team.current_points
        } for team in fslteams
    ]
    teams_data = sorted(teams_data_unsorted, key=lambda x: x["total_points"], reverse=True)
    return render_template("Tables.html", swepteams = swepteams, fslteams = teams_data)

@app.route("/transfers", methods=["GET"])
def showteam_and_players():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    if not user:
        return redirect("/")
    team = Team.query.filter_by(user_id=user.id).first()
    players = Player.query.all()
    if not team:
        return redirect("/")
    chosen_players = team.players
    remaining_budget = team.remaining_budget
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id : team.team_name for team in swepteam}
    
    return render_template("Transfers.html", team=chosen_players, players = players, team_budget = remaining_budget, teamnames = teamdict)

@app.route("/maketransfer" , methods=["GET","POST"])
def make_transfer():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    team = Team.query.filter_by(user_id=user.id).first()
    if not user:
        return redirect("/")
    if not team:
        return jsonify({"error": "Team not found"}), 404

    data = request.get_json()
    new_player_ids = data.get('players')

    if not new_player_ids:
        return jsonify({"error": "No players provided"}), 400

    new_players = Player.query.filter(Player.id.in_(new_player_ids)).all()

    if len(new_player_ids) != len(new_players):
        return jsonify({"error": "Some players not found"}), 404

    budget_remaining = team.remaining_budget
    total_price_new_players = sum(player.price for player in new_players)

    current_players = team.players
    total_price_current_players = sum(player.price for player in current_players)

    if total_price_new_players > total_price_current_players + budget_remaining:
        return jsonify({"error": "Not enough budget remaining"}), 400

    team.players = new_players
    db.session.commit()
    return redirect("/transfers"), 200

@app.route("/points", methods=["GET"])
def display_points():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    if not user:
        return redirect("/")
    team = Team.query.filter_by(user_id=user.id).first()
    players = team.players
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id : team.team_name for team in swepteam}
    return render_template("Points.html", players = players, team = team , teamnames = teamdict)

@app.route("/myteam", methods=["Get", "Post"])
def manage_team():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    if not user:
        return redirect("/")
    team = Team.query.filter_by(user_id=user.id).first()
    remaining_budget = team.remaining_budget
    if not team:
        return redirect("/")
    chosen_players = team.players
    captain = team.captain
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id : team.team_name for team in swepteam}
    return render_template("Myteam.html" , user = user , team = chosen_players, teamnames = teamdict, remaining_budget = remaining_budget, captain = captain)


@app.route('/change_captain', methods = ['Get'])
def change_captain():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    if not user:
        return jsonify({"error": "No user found"}), 400
    team = Team.query.filter_by(user_id=user.id).first()
    if not team:
        return jsonify({"error": "Team not found"}), 404
    data = request.args.get("captain")
    if not data :
        return jsonify({'error': 'no data found'})
    team.captain_id = int(data)
    captain = Player.query.filter_by(id = int(data)).first()
    if not captain:
        return jsonify({'error': 'Player not Found'})
    team.captain = captain
    db.session.commit()
    return jsonify({"success": 'Captain Changed Succesfully'})

@app.route("/filter_pickteam", methods=["Get","Post"])
def filter_pickteams():
    positions_list = ["Attacker", "Goalkeeper", "Midfielder", "Defender"]
    filter = request.args.get("argument")
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id : team.team_name for team in swepteam}
    players = []
    if filter.isnumeric() :
        Allplayers = Player.query.all()
        players = [ player for player in Allplayers if player.price >= float(filter)]
    elif filter in positions_list :
        players = Player.query.filter_by(position = filter)
    elif filter :
        Allplayers = Player.query.all()
        players = [player for player in Allplayers if filter.lower() in player.name.lower()]
        if not players or filter == "All" or filter == "0":
            players = Player.query.all()
            return render_template("pickteamfilter.html", players = players, price = filter,  teamnames = teamdict)
    return render_template("pickteamfilter.html", players = players, price = filter,  teamnames = teamdict)

@app.route("/filter", methods=["Get","Post"])
def filter():
    positions_list = ["Attacker", "Goalkeeper", "Midfielder", "Defender"]
    filter = request.args.get("argument")
    swepteam = SwepLeagueTeam.query.all()
    teamlist = [team.team_name for team in swepteam]
    teamdict = {team.id : team.team_name for team in swepteam}
    teamname = {name : id for id, name in teamdict.items()}
    players = []
    if filter.isnumeric() :
        Allplayers = Player.query.all()
        players = [ player for player in Allplayers if player.price >= float(filter)]
    elif filter in positions_list :
        players = Player.query.filter_by(position = filter)
    elif filter in teamlist:
        players = Player.query.filter_by(SwepLeagueTeam_id = teamname.get(filter))
    elif filter :
        Allplayers = Player.query.all()
        players = [player for player in Allplayers if filter.lower() in player.name.lower()]
        if not players or filter == "All":
            players = Player.query.all()
            return render_template("filter.html", players = players, price = filter,  teamnames = teamdict)
    return render_template("filter.html", players = players, price = filter,  teamnames = teamdict)

@app.route("/challenge", methods=["Get", "Post"])
def challenge():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    return render_template("Challenge.html",user = user )


@app.route("/enterchallenge", methods=["Get", "Post"])
def enter_challenge():
    current_user = session.get("user_id")
    user = User.query.filter_by(id=current_user).first()
    gameweek = GameWeek.get_current_week()
    challenge = UserChallenge(user_id=user.id, challenge_gameweek=gameweek)
    db.session.add(challenge)
    db.session.commit()
    return redirect("/predict")

@app.route("/predict", methods = ["Get", "Post"])
def enter_predictions():
    if request.method == "POST":
        current_user = session.get("user_id")
        user = User.query.filter_by(id=current_user).first()
        predictions = request.form.to_dict()
        try:
            gameweek = GameWeek.get_current_week()
            user = User.query.filter_by(id=current_user).first()
            challenge = UserChallenge.query.filter_by(user_id=user.id, challenge_gameweek=gameweek).first()
            if not challenge:
                return render_template("Challenge.html", msg="Pay for this gameweek challenge", user = user)
            for fixture_id, prediction in predictions.items():
                user_prediction = UserPrediction(
                    challenge_id=challenge.id,
                    fixture_id=fixture_id,
                    prediction=prediction
                )
                db.session.add(user_prediction)

            db.session.commit()
            return render_template("Challenge.html", msg = "Predictions submitted successfully", user = user), 200
        except Exception as e:
            error = str(e)
            db.session.rollback()
            return render_template("Challenge.html", msg = error, user = user), 500
    else:
        swepteam = SwepLeagueTeam.query.all()
        teamdict = {team.id : team.team_name for team in swepteam}
        gameweek = GameWeek.get_current_week()
        fixtures = Fixture.query.filter_by(game_week = gameweek).all()
        return render_template("play_challenge.html", fixtures = fixtures, teamnames = teamdict )




@app.route("/admin", methods=["Get","Post"])
def admin():
    password = request.args.get("fslpass")
    if password and password == "fsladmin":
        return render_template("admin.html")
    else:
        return redirect("/")

@app.route("/create_fixt", methods=["Get", "Post"])
def create_fixt():
    if request.method == "POST":
        data = request.form.to_dict()
        game_week = int(data.get("gameweek"))
        home_team_name = data.get("home_team")
        away_team_name = data.get("away_team")
        kickoff_time_str = data.get("date")
        kickoff_time = datetime.strptime(kickoff_time_str, '%Y-%m-%d').date()
        
        home_team = SwepLeagueTeam.query.filter_by(team_name=home_team_name).first()
        away_team = SwepLeagueTeam.query.filter_by(team_name=away_team_name).first()
        
        existing_fixture = Fixture.query.filter_by(
            home_team=home_team,
            away_team=away_team,
            kickoff_time=kickoff_time
        ).first()
        
        if existing_fixture:
            return render_template("admin.html", msg="Duplicate fixture found!")
        
        new_fixture = Fixture(
            game_week=game_week,
            home_team=home_team,
            away_team=away_team,
            kickoff_time=kickoff_time
        )
        
        db.session.add(new_fixture)
        db.session.commit()

        return render_template("admin.html", msg="Fixtures Created")
    else:
        swepteam = SwepLeagueTeam.query.all()
        teamlist = [team.team_name for team in swepteam]
        return render_template("create_fixture.html", teams=teamlist)
    
@app.route("/update_match", methods=["GET", "POST"])
def update_matches():
    if request.method == "POST":
        data = request.form.to_dict()
        home_team_name = data.get("home_team")
        away_team_name = data.get("away_team")
        home_score = int(data.get("home_score", 0))
        away_score = int(data.get("away_score", 0))

        saves = {}
        goals = {}
        assists = {}

        for key, value in request.form.items():
            if key.startswith("saves["):
                player_id = int(key.split('[')[1].split(']')[0])
                saves[player_id] = int(value) if value else 0
            elif key.startswith("goals["):
                player_id = int(key.split('[')[1].split(']')[0])
                goals[player_id] = int(value) if value else 0
            elif key.startswith("assists["):
                player_id = int(key.split('[')[1].split(']')[0])
                assists[player_id] = int(value) if value else 0

        yellow_cards = [int(player_id) for player_id in request.form.getlist("yellowcards")]
        red_cards = [int(player_id) for player_id in request.form.getlist("redcards")]

        home_team = SwepLeagueTeam.query.filter_by(team_name=home_team_name).first()
        away_team = SwepLeagueTeam.query.filter_by(team_name=away_team_name).first()

        if not home_team or not away_team:
            return render_template("admin.html", msg="One or both teams not found")

        fixture = Fixture.query.filter_by(home_team_id=home_team.id, away_team_id=away_team.id).first()

        if not fixture:
            return render_template("admin.html", msg="Fixture not Found")

        match = Match.query.filter_by(fixture_id=fixture.id).first()
        if match:
            match.home_score = home_score
            match.away_score = away_score
        else:
            match = Match(
                fixture_id=fixture.id,
                game_week=fixture.game_week,
                home_team_id=fixture.home_team_id,
                away_team_id=fixture.away_team_id,
                kickoff_time=fixture.kickoff_time,
                home_score=home_score,
                away_score=away_score
            )
            db.session.add(match)

        db.session.query(match_saves).filter_by(match_id=match.id).delete()
        db.session.query(match_goals).filter_by(match_id=match.id).delete()
        db.session.query(match_assists).filter_by(match_id=match.id).delete()
        db.session.query(match_yellow_cards).filter_by(match_id=match.id).delete()
        db.session.query(match_red_cards).filter_by(match_id=match.id).delete()

        for player_id, count in saves.items():
            if count > 0:
                db.session.execute(match_saves.insert().values(match_id=match.id, player_id=player_id, count=count))
        for player_id, count in goals.items():
            if count > 0:
                db.session.execute(match_goals.insert().values(match_id=match.id, player_id=player_id, count=count))
        for player_id, count in assists.items():
            if count > 0:
                db.session.execute(match_assists.insert().values(match_id=match.id, player_id=player_id, count=count))
        for player_id in yellow_cards:
            db.session.execute(match_yellow_cards.insert().values(match_id=match.id, player_id=player_id))
        for player_id in red_cards:
            db.session.execute(match_red_cards.insert().values(match_id=match.id, player_id=player_id))

        db.session.commit()

        db.session.refresh(match)

        print("Saves:", match.saves)
        print("Assists:", match.assists)
        print("Goals:", match.goals)
        print("Yellow Cards:", match.yellow_cards)
        print("Red Cards:", match.red_cards)

        return render_template("admin.html", msg="Match Updated")
    else:
        swepteam = SwepLeagueTeam.query.all()
        teamlist = [team.team_name for team in swepteam]
        players = Player.query.all()
        teamdict = {team.id: team.team_name for team in swepteam}

        return render_template("update_matches.html", teams=teamlist, players=players, teamnames=teamdict)    
    
@app.route("/adminfilter", methods=["Get", "Post"])
def adminfilter():
    home_name = request.args.get("home")
    away_name = request.args.get("away")
    if not home_name or not away_name:
        return "Home team or away team not specified", 400

    home_team = SwepLeagueTeam.query.filter_by(team_name=home_name).first()
    away_team = SwepLeagueTeam.query.filter_by(team_name=away_name).first()

    if home_team is None or away_team is None:
        return "One or both teams not found", 404

    Allplayers = Player.query.all()
    players = [player for player in Allplayers if player.SwepLeagueTeam_id == home_team.id or player.SwepLeagueTeam_id == away_team.id]
    swepteam = SwepLeagueTeam.query.all()
    teamdict = {team.id: team.team_name for team in swepteam}
    
    return render_template("adminfilter.html", players=players, teamnames=teamdict)
   
    
@app.route("/upload_points", methods=["GET", "POST"])
def upload_points():
    if request.method == "POST":
        data = request.form.to_dict()
        points = data
        errors = []
        try:
            for player_id, new_points in points.items():
                try:
                    new_points = int(new_points)
                    if not new_points:
                        new_points = 0
                    player = Player.query.filter_by(id = int(player_id)).first()
                    if player:
                        player.current_points = new_points
                    else:
                        errors.append(f"Player with ID {player_id} not found.")
                except ValueError:
                    errors.append(f"Invalid points value for player ID {player_id}.")
                    
            if errors:
                return render_template("admin.html", msg="Some errors occurred: " + ", ".join(errors))
            
            db.session.commit()
            return render_template("admin.html", msg="Points allocated successfully.")
        except Exception as e:
            db.session.rollback()
            return render_template("admin.html", msg=str(e))
    else:
        swepteam = SwepLeagueTeam.query.all()
        players = Player.query.all()
        return render_template("upload_points.html", Swepteams=swepteam, players=players)

@app.route("/set_new_gameweek", methods=["GET", "POST"])
def new_gameweek():
    if request.method == "POST":
        data = request.form.to_dict()
        answer = data.get("answer")
        if answer == "Yes":
            try:
                gameweek = GameWeek.get_current_week()
                user_challenges = UserChallenge.query.filter_by(challenge_gameweek=gameweek).all()
                
                for challenge in user_challenges:
                    correct_predictions = 0
                    for prediction in challenge.predictions:
                        match = Match.query.filter_by(fixture_id=prediction.fixture_id).first()
                        if match:
                            actual_result = "draw"
                            if match.home_score > match.away_score:
                                actual_result = "home win"
                            elif match.home_score < match.away_score:
                                actual_result = "away win"

                            if prediction.prediction == actual_result:
                                correct_predictions += 1

                    team = Team.query.filter_by( user_id = challenge.user.id).first()
                    if correct_predictions == 4:
                        team.total_points += 7
                    elif correct_predictions == 3:
                        team.total_points += 5
                    db.session.commit()

                players = Player.query.all()
                teams = Team.query.all()
                
                for team in teams:
                    team.add_total_points()
                for player in players:
                    player.reset_current_points()
                        
                GameWeek.increment_week()
                gameweek = GameWeek.get_current_week()
                return render_template("admin.html", msg=f"Gameweek {gameweek} set"), 200
            except Exception as e:
                db.session.rollback()
                return render_template("admin.html", msg=str(e)), 500
        else:
            return render_template("admin.html", msg="Action cancelled"), 200
    else:
        return render_template("set_new_gameweek.html"), 200
        
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect("/")


def load_swep_teams(csv_file):
    with open(csv_file, newline='') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            team = SwepLeagueTeam(
                team_name=row[0]
            )
            db.session.add(team)
        db.session.commit()

def load_players(csv_file):
    with open(csv_file, newline='') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            team = SwepLeagueTeam.query.filter_by(team_name=row[2]).first()
            if team:
                player = Player(
                    name=row[0],
                    position=row[1],
                    price=row[3],
                    SwepLeagueTeam_id=team.id
                )
                db.session.add(player)
        db.session.commit()   

with app.app_context():
    db.drop_all()
    db.create_all()
    load_swep_teams('Swepleageteams.csv')
    load_players('players.csv')
app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
