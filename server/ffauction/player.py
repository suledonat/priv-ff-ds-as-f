import json
import csv
import io
import psycopg2
import sys
import psycopg2.extras


class Player:
    def __init__(self):
        self.projected_points = 0.0
        self.starter_vbd = 0.0
        self.bench_vbd = 0.0
        self.avg_vbd = 0.0
        self.base_price = 0.0
        self.tier = 0
        self.name = "NA"
        self.player_id = "NAID"
        self.team = "UKN"
        self.position = "QB"

        self.passAtt = 0.0
        self.passComp = 0.0
        self.passYds = 0.0
        self.passTds = 0.0
        self.twoPts = 0.0
        self.sacks = 0.0
        self.passInt = 0.0
        self.rushAtt = 0.0
        self.rushYds = 0.0
        self.rushTds = 0.0
        self.rec = 0.0
        self.recYds = 0.0
        self.recTds = 0.0
        self.fumbles = 0.0

        self.adjFactor = 0.0

        self.fg = 0.0
        self.fgAtt = 0.0
        self.xpt = 0.0
        self.sack = 0.0
        self.defInt = 0.0
        self.fr = 0.0
        self.ff = 0.0
        self.defTd = 0.0
        self.safe = 0.0
        self.ptsAllowed = 0.0
        self.ydsVS = 0.0
        self.sos = 0.0


    def init_from_row(self, row):
        self.name = row['player']
        self.player_id = row['playerId']
        self.team = row['team']
        self.position = row['position']

        self.passAtt = float(row['passAtt'])
        self.passComp = float(row['passComp'])
        self.passYds = float(row['passYds'])
        self.passTds = float(row['passTds'])
        
        
        self.passInt = float(row['passInt'])
        self.rushAtt = float(row['rushAtt'])
        self.rushYds = float(row['rushYds'])
        self.rushTds = float(row['rushTds'])
        self.rec = float(row['rec'])
        self.recYds = float(row['recYds'])
        self.recTds = float(row['recTds'])
        self.fumbles = float(row['fumbles'])
        self.adjFactor = float(row['adjFactor'])

        self.fg = float(row['fg'])
        self.fgAtt = float(row['fgAtt'])
        self.xpt = float(row['xpt'])
        self.sack = float(row['sack'])
        self.defInt = float(row['defInt'])
        self.fr = float(row['fr'])
        self.ff = float(row['ff'])
        self.defTd = float(row['defTd'])
        self.safe = float(row['safe'])
        self.ptsAllowed = float(row['ptsAllowed'])
        self.ydsVS = float(row['ydsVS'])
        self.sos = float(row['sos'])


        self.twoPts = 0.0##float(row['twoPts']) depr in 2019
        self.sacks = 0.0 ##float(row['sacks']) depr in 2019



    def calc_points(self, scoring):
        self.projected_points = 0
        for action in scoring:
            self.projected_points += getattr(self, action, 0) * scoring[action]
        if self.position == "K":
            self.projected_points = 5.0
        elif self.position == "DST":
            self.projected_points = 5.0
        self.projected_points = self.projected_points * self.adjFactor

    def init_from_dict(self, data):
        for key in data:
            setattr(self, key, data[key])

    def __str__(self):
        return "%s\t%s\t%s\t%f\t%f\t%f\t%f" % (self.name, self.position,
                                               self.team, self.projected_points,
                                               self.starter_vbd, self.bench_vbd,
                                               self.base_price,self.sos)


class PlayerPriceJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Player):
            return {
                "player_id": obj.player_id,
                "name": obj.name,
                "position": obj.position,
                "team": obj.team,
                "points": obj.projected_points,
                "base_price": obj.base_price,
                "avg_vbd": obj.avg_vbd,
                "tier": obj.tier,
                "sos": obj.sos,
            }
        return json.JSONEncoder.default(self, obj)


class FullPlayerJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Player):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)


class PlayerSet:
    def __init__(self):
        self.QB = []
        self.RB = []
        self.WR = []
        self.TE = []
        self.K = []
        self.DST = []

    def get_position_players_by_position(self):
        return {
            'QB': self.QB,
            'RB': self.RB,
            'WR': self.WR,
            'TE': self.TE
        }

    def get_all(self):
        return self.QB + self.RB + self.WR + self.TE + self.K + self.DST

    # @TODO Add other flex types
    def get_flex(self, flex_type, qb, rb, wr, te, flex):
        if flex_type == "rb/wr/te":
            remaining_rb = self.RB[rb:]
            remaining_wr = self.WR[wr:]
            remaining_te = self.TE[te:]
            remaining = sorted(remaining_rb + remaining_wr + remaining_te,
                               key=lambda player: player.projected_points,
                               reverse=True)
            return remaining[:flex]

    def get_top_n(self, position_counts):
        for list_of_players in [self.QB, self.RB, self.WR, self.TE]:
            list_of_players.sort(key=lambda player: player.projected_points,
                                 reverse=True)
        top_n = {}
        for position in ["QB", "RB", "WR", "TE"]:
            top_n[position] = (getattr(self, position)
                               [:int(position_counts[position])])
        return top_n

    def load_list(self, players):
        for player_dict in players:
            player = Player()
            player.init_from_dict(player_dict)
            self.add_player(player)

    def load_projection_stats_from_csv(self, uploaded_file):
        projections = uploaded_file.stream.read()
        projectionsCsv = projections.decode('utf-8')
        projectionsStream = io.StringIO(projectionsCsv)
        reader = csv.reader(projectionsStream)
        headers = next(reader)
        for row in reader:
            player = Player()
            rowDict = {}
            for i in range(0, len(row)):
                rowDict[headers[i]] = row[i]

            player.init_from_row(rowDict)
            self.add_player(player)

    def load_projection_stats_DB(self, conn):
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM ff2019data;")
        for row in cur:
            player = Player()
            player.init_from_row(row)
            self.add_player(player)

    def add_player(self, player):
            if player.position == 'QB':
                self.QB.append(player)
            if player.position == 'RB':
                self.RB.append(player)
            if player.position == 'WR':
                self.WR.append(player)
            if player.position == 'TE':
                self.TE.append(player)
            if player.position == 'K':
                self.K.append(player)
            if player.position == 'DST':
                self.DST.append(player)

    def __str__(self):
        table_of_players = ""
        for list_of_players in [self.QB, self.RB, self.WR, self.TE]:
            for player in list_of_players:
                table_of_players += str(player) + "\n"
        return table_of_players
