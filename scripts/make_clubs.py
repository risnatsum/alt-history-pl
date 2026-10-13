"""One-off helper that generated data/reference/clubs.csv (kept for provenance).

Canonical club names follow the short form used by most English sources.
Aliases cover openfootball, engsoccerdata and football-data spellings.
"""
import csv, re, sys
from pathlib import Path

CANON = {
 # canonical name: [aliases]
 "AFC Wimbledon": [], "Accrington Stanley": ["Accrington"], "Aldershot Town": ["Aldershot"],
 "Alfreton Town": [], "Altrincham": [], "Arsenal": [], "Aston Villa": [], "Barnet": [],
 "Barnsley": [], "Barrow": [], "Bath City": [], "Birmingham City": ["Birmingham"],
 "Blackburn Rovers": ["Blackburn"], "Blackpool": [], "Bolton Wanderers": ["Bolton"],
 "Boreham Wood": [], "Boston United": ["Boston Utd"], "Bournemouth": ["AFC Bournemouth"],
 "Brackley Town": [], "Bradford City": ["Bradford"], "Braintree Town": [], "Brentford": [],
 "Brighton & Hove Albion": ["Brighton"], "Bristol City": [], "Bristol Rovers": ["Bristol Rvs"],
 "Bromley": [], "Burnley": [], "Burton Albion": ["Burton"], "Bury": [],
 "Cambridge United": ["Cambridge"], "Cardiff City": ["Cardiff"], "Carlisle United": ["Carlisle"],
 "Charlton Athletic": ["Charlton"], "Chelsea": [], "Cheltenham Town": ["Cheltenham"],
 "Chester City": [], "Chester": [], "Chesterfield": [], "Chorley": [],
 "Colchester United": ["Colchester"], "Coventry City": ["Coventry"], "Crawley Town": [],
 "Crewe Alexandra": ["Crewe"], "Crystal Palace": [],
 "Dagenham & Redbridge": ["Dagenham and Redbridge", "Dag and Red"], "Darlington": [],
 "Dartford": [], "Derby County": ["Derby"], "Doncaster Rovers": ["Doncaster"],
 "Dorking Wanderers": ["Dorking"], "Dover Athletic": [], "Eastbourne Borough": [],
 "Eastleigh": [], "Ebbsfleet United": ["Ebbsfleet"], "Everton": [], "Exeter City": ["Exeter"],
 "Fleetwood Town": [], "Forest Green Rovers": ["Forest Green"], "Fulham": [],
 "AFC Fylde": ["Fylde"], "Gateshead": [], "Gillingham": [], "Grays Athletic": ["Grays"],
 "Grimsby Town": ["Grimsby"], "Guiseley": [], "FC Halifax Town": ["Halifax Town", "Halifax"],
 "Harrogate Town": ["Harrogate Town A.F.C.", "Harrogate"], "Hartlepool United": ["Hartlepool"],
 "Havant & Waterlooville": [], "Hayes & Yeading United": ["Hayes & Yeading"],
 "Hereford United": ["Hereford"], "Histon": [], "Hornchurch": [],
 "Huddersfield Town": ["Huddersfield"], "Hull City": ["Hull"], "Hyde United": ["Hyde"],
 "Ipswich Town": ["Ipswich"], "Kettering Town": [], "Kidderminster Harriers": ["Kidderminster"],
 "King's Lynn Town": ["King's Lynn"], "Leeds United": ["Leeds"],
 "Leicester City": ["Leicester"], "Lewes": [], "Leyton Orient": [], "Lincoln City": ["Lincoln"],
 "Liverpool": [], "Luton Town": ["Luton"], "Macclesfield Town": ["Macclesfield"],
 "Maidenhead United": ["Maidenhead"], "Maidstone United": ["Maidstone"],
 "Manchester City": ["Man City"], "Manchester United": ["Man United"],
 "Mansfield Town": ["Mansfield"], "Middlesbrough": [], "Millwall": [],
 "Milton Keynes Dons": ["MK Dons"], "Morecambe": [], "Newcastle United": ["Newcastle"],
 "Newport County": [], "North Ferriby United": ["North Ferriby"],
 "Northampton Town": ["Northampton"], "Northwich Victoria": ["Northwich"], "Norwich City": ["Norwich"],
 "Nottingham Forest": ["Nott'm Forest", "Nottm Forest"], "Notts County": [],
 "Nuneaton Borough": ["Nuneaton Town"], "Oldham Athletic": ["Oldham"], "Oxford City": [],
 "Oxford United": ["Oxford"], "Peterborough United": ["Peterboro"],
 "Plymouth Argyle": ["Plymouth"], "Port Vale": [], "Portsmouth": [],
 "Preston North End": ["Preston"], "Queens Park Rangers": ["QPR"], "Reading": [],
 "Rochdale": [], "Rotherham United": ["Rotherham"], "Rushden & Diamonds": ["Rushden & D"],
 "Salford City": ["Salford"], "Salisbury City": ["Salisbury"],
 "Scunthorpe United": ["Scunthorpe"], "Sheffield United": [],
 "Sheffield Wednesday": ["Sheffield Weds"], "Shrewsbury Town": ["Shrewsbury"],
 "Solihull Moors": ["Solihull"], "Southampton": [], "Southend United": ["Southend"],
 "Southport": [], "Stevenage": ["Stevenage Borough"], "Stockport County": ["Stockport"],
 "Stoke City": ["Stoke"], "Sunderland": [], "Sutton United": ["Sutton"],
 "Swansea City": ["Swansea"], "Swindon Town": ["Swindon"], "Tamworth": [],
 "AFC Telford United": ["Telford United"], "Torquay United": ["Torquay"],
 "Tottenham Hotspur": ["Tottenham"], "Tranmere Rovers": ["Tranmere"], "Truro City": ["Truro"],
 "Walsall": [], "Watford": [], "Wealdstone": [], "Welling United": [],
 "West Bromwich Albion": ["West Brom"], "West Ham United": ["West Ham"], "Weymouth": [],
 "Wigan Athletic": ["Wigan"], "Woking": [], "Wolverhampton Wanderers": ["Wolves"],
 "Worthing": [], "Wrexham": [], "Wycombe Wanderers": ["Wycombe"], "Yeovil Town": ["Yeovil"],
 "York City": ["York"],
}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower().replace("&", "and")).strip("_")


if __name__ == "__main__":
    out = Path(sys.argv[1])
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["club_id", "name", "aliases"])
        for name in sorted(CANON, key=str.lower):
            w.writerow([slug(name), name, "|".join(CANON[name])])
