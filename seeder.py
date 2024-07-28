import csv
from app import app, db, Player, SwepLeagueTeam

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