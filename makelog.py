import psycopg2
import psycopg2.extras

db = psycopg2.connect(dbname='ham_station')

t_date_start = "2021-03-02 18:00:00"
t_date_stop = "2021-03-02 22:00:00"
t_name = "NAC 144 Mar 2021"


prefixes = {
    "LA": "NO",
    "LG": "NO",
    "SA": "SE",
    "SB": "SE",
    "SC": "SE",
    "SD": "SE",
    "SE": "SE",
    "SF": "SE",
    "SG": "SE",
    "SH": "SE",
    "SI": "SE",
    "SJ": "SE",
    "SK": "SE",
    "SL": "SE",
    "SM": "SE",
    "8S": "SE",
    "7S": "SE",
    "OZ": "DK",
    "DL": "DE",
    "DK": "DE",
    "DG": "DE"

}


contest_log_header = {
    "TName": "NAC 144",  # Contest name
    "TDate": None,  # Beginning;Ending date of contest
    "PCall": None,  # Beginning;Ending date of contest
    "PWWLo": None,  # WWL used
    "PExch": None,  # Exchanged info used
    "PAdr1": None,  # Address used line 1
    "PAdr2": None,  # Address used line 2
    "PSect": None,  # Contest section/class/category/group
    "PBand": "144 MHz",  # Frequency band
    "PClub": None,  # Associated club call
    "RName": None,  # Name of responsible operator
    "RCall": None,  # Callsign of responsible op
    "RAdr1": None,  # Address of responsible op line 1
    "RAdr2": None,  # Address of responsible op line 2
    "RPoCo": None,  # Postal code of responsible op
    "RCity": None,  # City of responsible op
    "RCoun": None,  # Country of responsible op
    "RPhon": None,  # Phone no of responsible op
    "RHBBS": None,  # BBS or email of responsible op
    "MOpe1": None,  # Operators line 1
    "MOpe2": None,  # Operators line 2
    "STXEq": None,  # Transmitting equipment
    "SPowe": None,  # Transmitting power
    "SRXEq": None,  # Receiving equipment
    "SAnte": None,  # Antenna system description
    "SAntH": None,  # Antenna AGl;ASl
    "CQSOs": None,  # # of valid QSOS;Band mutiplier
    "CWWLs": None,  # Claimed # of WWLs wkd;Bonus per WWL;WWL multiplier
    "CWWLB": None,  # Claimed WWL bonus points
    "CExcs": None,  # Claimed exchanges; Bonus per exchange; Multiplier per exchange
    "CExcB": None,  # Claimed exchange bonus points
    "CDXCs": None,  # Claimed DXCCs; bonus points per DXCC; DCXX multiplier
    "CDXCB": None,  # Claimed DXCC bonus points
    "CToSc": None,  # Claimed total score
    "CODXC": None,  # Claimed ODX call; WWL; distance
}

nac_initials = {
    "TName": "NAC 144",
    "PBand": "144 MHz",
    "CWWLs": ";500;1",
    "CExcs": ";0;1",
    "CDXCs": ";0;1",
    "CQSOs": ";1"
}

log = contest_log_header.copy()
for k, v in nac_initials.items():
    log[k] = v

cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

ts = t_date_start[:10]

log["TDate"] = t_date_start[:10].replace("-", "")

cur.execute(
    "SELECT * FROM config_str WHERE (time_start IS NULL OR time_start <= %s ) AND (time_stop IS NULL OR time_stop >= %s) ORDER BY key",
    (ts, ts)
)
rows = cur.fetchall()

for row in rows:
    k = row["key"]
    v = row["value"]
    if k == "my_callsign":
        log["PCall"] = log["RCall"] = v
    elif k == "my_locator":
        log["PWWLo"] = v[:6]
    elif k == "my_address":
        log["RAdr1"] = log["PAdr1"] = v
    elif k == "my_club":
        log["PClub"] = v
    elif k == "my_name":
        log["RName"] = v
    elif k == "my_postcode":
        log["RPoCo"] = v
    elif k == "my_city":
        log["RCity"] = v
    elif k == "my_country":
        log["RCoun"] = v
    elif k == "my_phone":
        log["RPhon"] = v
    elif k == "my_email":
        log["RHBBS"] = v
    elif k == "my_tx":
        log["STXEq"] = v
    elif k == "my_pwr":
        log["SPowe"] = v
    elif k == "my_rx":
        log["SRXEq"] = v
    elif k == "my_ant":
        log["SAnte"] = v
    elif k == "my_ant_agl":
        log["SAntH"] = str(v)
    elif k == "my_ant_asl":
        log["SAntH"] += ";" + str(v)
    else:
        pass

pass

args = (t_date_start[:10], t_date_stop[:10], t_date_start[11:16].replace(":", ""), t_date_stop[11:16].replace(":", ""))
cur.execute(
    "SELECT DISTINCT(callsign) FROM nac_log_new WHERE date >= %s and date <= %s and time >= %s and time <= %s",
    args)
rows = cur.fetchall()
qso_records = len(rows)
band_multiplier = int(log["CQSOs"].split(";")[1])
log["CQSOs"] = str(len(rows)) + ";" + str(band_multiplier)

print("[REG1TEST,1]")

cur.execute("SELECT SUM(points) from nac_log_new WHERE date >= %s and date <= %s and time >= %s and time <= %s", args)
total_points = cur.fetchall()[0]['sum']

wwls, wwl_bonus, wwl_multiplier = log["CWWLs"].split(";")

cur.execute("SELECT DISTINCT SUBSTR(locator, 1, 4) FROM nac_log_new WHERE date >= %s and date <= %s and time >= %s and time <= %s", args)
wwls = len(cur.fetchall())

log["CWWLs"] = "%d;%s;%s" % (wwls, wwl_bonus, wwl_multiplier)
log["CWWLB"] = wwls * int(wwl_bonus) * int(wwl_multiplier)

cur.execute("SELECT DISTINCT callsign, date, time  FROM nac_log_new WHERE date >= %s and date <= %s and time >= %s and time <= %s ORDER BY date, time", args)

wkd_countries=set()

for row in cur.fetchall():
    call = row["callsign"].upper()

    for pfx in prefixes:
        if call.startswith(pfx):
            country = prefixes[pfx]
            if country not in wkd_countries:
                new_dxcc = "N"
                wkd_countries.add(country)
            break
    else:
        raise LookupError("Unknown prefix for callsign %s" % call)

dxccs, dxcc_bonus, dxcc_multiplier = log["CDXCs"].split(";")

log["CDXCs"] = "%s;%s;%s" % (len(wkd_countries), dxcc_bonus, dxcc_multiplier)
log["CQSOP"] = total_points + len(wkd_countries) * int(dxcc_bonus) * int(dxcc_multiplier) - int(wwl_bonus) * wwls
log["CToSc"] = total_points + len(wkd_countries) * int(dxcc_bonus) * int(dxcc_multiplier)

cur.execute(""" SELECT callsign, locator, distance FROM nac_log_new WHERE date >= %s and date <= %s and time >= %s and time <= %s ORDER BY distance DESC""", args)
odxrow = cur.fetchall()[0]
log["CODXC"] = "%s;%s;%s" % (odxrow["callsign"].upper(), odxrow["locator"].upper(), odxrow["distance"])


for key, value in log.items():
    print("%s=%s" % (key, value))
print("[QSORecords;%d]" % qso_records)

wkd_countries = set()
wkd_calls = set()

cur.execute("SELECT * FROM nac_log_new WHERE date >= %s and date <= %s and time >= %s and time <= %s ORDER BY date, time", args)
rows = cur.fetchall()

for row in rows:
    date = row["date"][2:].replace("-", "")
    time = row["time"]
    call = row["callsign"].upper()
    if len(row["tx"]) > 2 and len(row["rx"]) > 2:
        mode_code = "2"  # TWO Way CW
    elif len(row["tx"]) == 2 and len(row["rx"]) > 2:
        mode_code = "3"  # TX SSB, RX CW
    elif len(row["tx"]) == 2 and len(row["rx"]) == 2:
        mode_code = "1"  # TWO Way SSB
    elif len(row["tx"]) > 2 and len(row["rx"]) == 2:
        mode_code = "4"  # TX CW, RX SSB
    else:
        mode_code = "0"  # Don't know

    tx = row["tx"].upper()
    tx_qson = ""
    rx = row["rx"].upper()
    rx_qson = ""
    rx_exch = ""
    rx_wwl = row["locator"].upper()
    qso_points = int(row["points"]) * band_multiplier - int(wwl_bonus) * (1 if row["square"] else 0)
    new_exchange = ""
    new_wwl = "N" if row["square"] else ""
    new_dxcc = ""

    for pfx in prefixes:
        if call.startswith(pfx):
            country = prefixes[pfx]
            if country not in wkd_countries:
                new_dxcc = "N"
                wkd_countries.add(country)
            break
    else:
        raise LookupError("Unknown prefix for callsign %s" % call)

    dup_qso = ""
    if call in wkd_calls:
        dup_qso = "D"
    wkd_calls.add(call)

    print("%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%d;%s;%s;%s;%s" %
          (date, time, call, mode_code,
          tx, tx_qson, rx, rx_qson, rx_exch, rx_wwl,
          qso_points, new_exchange, new_wwl, new_dxcc, dup_qso))


