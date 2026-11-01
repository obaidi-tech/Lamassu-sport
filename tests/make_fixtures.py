"""Generate OFFLINE TEST FEEDS (fictional events) so the engine can be tested without internet.
None of these headlines are real news."""
import os
import random
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
FX = os.path.join(HERE, "fixtures")
random.seed(7)

PUBS = ["Reuters", "AP News", "AFP", "BBC Sport", "ESPN", "The Guardian", "Sky Sports", "Marca",
        "Goal.com", "Football Insider", "Sports Daily Blog"]

# (headline, summary, number_of_publishers)
STORIES = [
    # top5 – Premier League
    ("Arsenal confirm Saka fitness ahead of Brighton trip", "[TEST] Arsenal said winger Bukayo Saka trained fully on Thursday before Saturday's game.", 5),
    ("Liverpool beat Aston Villa 3-1 to stay top of Premier League", "[TEST] Liverpool won 3-1 at Anfield with two second-half goals.", 6),
    ("Manchester City name new sporting director", "[TEST] Manchester City appointed a new sporting director on a contract until 2029.", 4),
    ("Chelsea manager says squad needs time after Newcastle draw", "[TEST] Chelsea drew 2-2 at Newcastle and the manager asked fans for patience.", 3),
    # LaLiga
    ("Real Madrid edge Sevilla 2-1 at the Bernabeu", "[TEST] Real Madrid came from behind to beat Sevilla 2-1 in LaLiga.", 6),
    ("Barcelona reportedly in talks with Bundesliga winger", "[TEST] Barcelona are reportedly in talks over a 40 million euro deal.", 1),
    ("Atletico Madrid extend Simeone contract to 2028", "[TEST] Atletico Madrid announced a contract extension for their coach until 2028.", 4),
    ("Villarreal striker ruled out for six weeks with hamstring injury", "[TEST] Villarreal confirmed a six-week absence for their top scorer.", 2),
    # Bundesliga
    ("Bayern Munich thrash Stuttgart 5-0 in Bundesliga", "[TEST] Bayern scored five times against Stuttgart, with a hat-trick from their striker.", 5),
    ("Dortmund appoint former academy coach as assistant", "[TEST] Borussia Dortmund promoted a youth coach to the first-team staff.", 2),
    ("Leverkusen captain signs new deal until 2030", "[TEST] Bayer Leverkusen captain committed his future to the club until 2030.", 3),
    # Serie A
    ("Inter Milan go top of Serie A after win over Lazio", "[TEST] Inter Milan beat Lazio 2-0 and moved one point clear at the top.", 5),
    ("Juventus confirm knee surgery for defender", "[TEST] Juventus said the defender underwent successful knee surgery.", 3),
    ("Napoli and AC Milan share points in 1-1 draw", "[TEST] Napoli and AC Milan drew 1-1 in Naples.", 4),
    # Ligue 1
    ("PSG beat Marseille 3-0 in Le Classique", "[TEST] Paris Saint-Germain won 3-0 against Marseille in Ligue 1.", 6),
    ("Monaco unveil new training centre investment", "[TEST] Monaco announced a 25 million euro upgrade of its training base.", 2),
    ("Lyon sack coach after five straight Ligue 1 defeats", "[TEST] Lyon dismissed their head coach after a fifth consecutive loss.", 4),
    # orgs
    ("FIFA publishes revised calendar for international windows", "[TEST] FIFA's council approved changes to the international match calendar.", 5),
    ("UEFA opens disciplinary case after Europa League match", "[TEST] UEFA said its disciplinary body will review incidents from the match.", 4),
    ("IOC confirms host selection timeline for 2036 Olympics", "[TEST] The International Olympic Committee set out the next steps for 2036.", 4),
    ("Asian Football Confederation announces Champions League draw date", "[TEST] The AFC will hold the draw in Kuala Lumpur next month.", 3),
    ("CONMEBOL sets dates for Copa Libertadores final", "[TEST] CONMEBOL confirmed the final venue and date.", 3),
    ("World Athletics approves new competition rules", "[TEST] World Athletics council approved rule changes for the coming season.", 2),
    ("FIBA unveils qualifying format for basketball World Cup", "[TEST] FIBA presented the new qualifying windows.", 2),
    # nba
    ("Lakers beat Celtics 118-112 behind LeBron James", "[TEST] LeBron James scored 31 points as the Lakers won 118-112.", 6),
    ("Wembanyama posts triple-double in Spurs win", "[TEST] Victor Wembanyama recorded a triple-double in San Antonio's victory.", 5),
    ("Nuggets sign veteran guard to two-year deal", "[TEST] Denver Nuggets agreed a two-year contract with a veteran guard.", 3),
    ("Knicks extend winning streak to seven games", "[TEST] The Knicks won their seventh straight game.", 4),
    # other sports
    ("Sinner wins Paris Masters title", "[TEST] Jannik Sinner won the tennis title in straight sets.", 6),
    ("Sabalenka withdraws from WTA event with illness", "[TEST] Aryna Sabalenka pulled out of the WTA tournament.", 3),
    ("Verstappen takes pole for Brazilian Grand Prix", "[TEST] Max Verstappen qualified first for the Formula 1 race.", 6),
    ("Norris says McLaren upgrades are working", "[TEST] Lando Norris praised McLaren's latest Formula 1 upgrades.", 2),
    ("Kenyan runner breaks course record at marathon", "[TEST] A Kenyan athlete broke the marathon course record by 40 seconds.", 4),
    ("Diamond League final schedule announced", "[TEST] Organisers released the athletics Diamond League schedule.", 2),
    ("Usyk to defend heavyweight titles in Riyadh", "[TEST] Oleksandr Usyk will defend his heavyweight boxing belts in Riyadh.", 5),
    ("UFC confirms main event for December card", "[TEST] The UFC confirmed the main event of its December card.", 3),
    ("Ryder Cup captains named for next edition", "[TEST] Golf's Ryder Cup captains were announced for the next edition.", 3),
    ("India beat Australia in first Test match", "[TEST] India won the opening cricket Test match by 7 wickets.", 4),
    ("Six Nations fixtures released for 2027", "[TEST] Rugby Six Nations organisers published the 2027 fixtures.", 3),
    ("Pogacar confirms Tour de France participation", "[TEST] Tadej Pogacar will ride the Tour de France, his team said.", 4),
    ("Swimming world record falls in short course meet", "[TEST] A swimming world record was broken in the 200m event.", 3),
    ("MotoGP champion signs contract extension", "[TEST] The MotoGP champion extended his deal with his team.", 2),
    ("Chiefs beat Bills in NFL thriller", "[TEST] Kansas City won a close NFL game against Buffalo.", 4),
    # world football
    ("Al-Hilal win Saudi Pro League derby against Al-Nassr", "[TEST] Al-Hilal beat Al-Nassr 2-1 in the Saudi league derby.", 5),
    ("Inter Miami reach MLS conference final", "[TEST] Inter Miami advanced in the MLS playoffs.", 5),
    ("Flamengo clinch Brasileirao lead with win over Palmeiras", "[TEST] Flamengo moved top of Brazil's league after beating Palmeiras.", 4),
    ("Boca Juniors appoint new coach", "[TEST] Argentina's Boca Juniors named a new head coach.", 3),
    ("Benfica beat Porto in Portuguese top-of-table clash", "[TEST] Benfica won 2-0 against Porto.", 4),
    ("Galatasaray extend lead in Turkey after derby win", "[TEST] Galatasaray beat Fenerbahce in Istanbul.", 4),
    ("Celtic and Rangers draw Old Firm derby", "[TEST] Celtic and Rangers drew 1-1 in Scotland.", 3),
    ("Ajax hire new technical director", "[TEST] Ajax in the Eredivisie appointed a technical director.", 2),
    ("Al Ahly win Egyptian league clash against Zamalek", "[TEST] Al Ahly beat Zamalek 1-0 in Egypt.", 3),
    ("Wydad name new coach before African season", "[TEST] Morocco's Wydad appointed a coach.", 2),
    ("Liga MX final set after semi-final second legs", "[TEST] Mexico's Liga MX final pairing is confirmed.", 2),
    ("Al Sadd top Qatar Stars League after victory", "[TEST] Al Sadd won to go top in Qatar.", 2),
    ("Japan J-League title race goes to final day", "[TEST] The J1 League title will be decided on the final day in Japan.", 2),
    ("Former striker dies aged 71", "[TEST] A former international striker has died aged 71, his club said.", 4),
    # awareness
    ("Study finds heading training linked to concussion risk in youth players", "[TEST] Researchers published a study on concussion and heading.", 3),
    ("Athletes mental health programme launched by players union", "[TEST] A union launched a mental health support programme for athletes.", 2),
    ("WADA publishes updated prohibited list", "[TEST] WADA released the updated list of banned substances.", 3),
    ("Fact check: viral transfer video is fake, club says", "[TEST] A club said a viral video about a transfer was fake news.", 2),
]

AR_STORIES = [
    ("الهلال يفوز على النصر في ديربي الرياض", "[TEST] فاز الهلال على النصر 2-1 في الدوري السعودي.", 3),
    ("منتخب العراق يستعد لمعسكر تدريبي في الدوحة", "[TEST] يبدأ منتخب العراق معسكره التدريبي الأسبوع المقبل.", 2),
    ("الاتحاد الآسيوي يحدد موعد قرعة دوري الأبطال", "[TEST] أعلن الاتحاد الآسيوي موعد القرعة.", 2),
]

OPINIONS = [
    ("The Premier League's fixture pile-up is a warning nobody is heeding", "Test Columnist A",
     "[TEST] The columnist argues player welfare is being ignored as calendars grow."),
    ("Why LaLiga's spending rules are reshaping Spanish football", "Test Columnist B",
     "[TEST] The writer says financial controls have changed how clubs recruit."),
    ("Women's football needs better grassroots pitches, not slogans", "Test Columnist C",
     "[TEST] The piece calls for investment in community facilities."),
    ("The NBA's load management debate misses the point", "Test Columnist D",
     "[TEST] The author argues rest policy should focus on schedule design."),
    ("Olympic host cities need a new model", "Test Columnist A",
     "[TEST] A second piece by the same writer on Olympic costs."),
]

VARIANT_PREFIX = ["", "", "Report: ", "Update: ", "Watch: "]


def rss(items, title="Test feed"):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>',
           f"<title>{escape(title)}</title>"]
    for it in items:
        out.append("<item>")
        out.append(f"<title>{escape(it['title'])}</title>")
        out.append(f"<link>{escape(it['link'])}</link>")
        out.append(f"<description>{escape(it['summary'])}</description>")
        out.append(f"<pubDate>{format_datetime(it['date'])}</pubDate>")
        if it.get("source"):
            out.append(f'<source url="https://example.com">{escape(it["source"])}</source>')
        if it.get("author"):
            out.append(f"<dc:creator>{escape(it['author'])}</dc:creator>")
        out.append("</item>")
    out.append("</channel></rss>")
    return "\n".join(out)


def main():
    os.makedirs(FX, exist_ok=True)
    now = datetime.now(timezone.utc)
    gn, gn_ar, opinion = [], [], []
    n = 0
    for head, summ, k in STORIES:
        pubs = ["Football Insider"] if k == 1 else random.sample(PUBS[:9], k)
        for j, p in enumerate(pubs):
            n += 1
            gn.append({"title": f"{VARIANT_PREFIX[j % 5]}{head} - {p}", "summary": summ,
                       "link": f"https://example.com/test/{n}", "source": p,
                       "date": now - timedelta(hours=random.uniform(0.5, 20))})
    for head, summ, k in AR_STORIES:
        for j, p in enumerate(["الجزيرة", "موقع رياضي", "صحيفة محلية"][:k]):
            n += 1
            gn_ar.append({"title": f"{head} - {p}", "summary": summ, "link": f"https://example.com/test/{n}",
                          "source": p, "date": now - timedelta(hours=random.uniform(1, 15))})
    for head, author, summ in OPINIONS:
        n += 1
        opinion.append({"title": head, "summary": summ, "author": author,
                        "link": f"https://example.com/test/{n}", "date": now - timedelta(hours=random.uniform(2, 30))})
    old = [{"title": "Old story that must be ignored - Reuters", "summary": "[TEST] too old", "source": "Reuters",
            "link": "https://example.com/test/old", "date": now - timedelta(hours=60)}]

    for name, items in [("gnews_en.xml", gn + old), ("gnews_ar.xml", gn_ar), ("opinion.xml", opinion)]:
        with open(os.path.join(FX, name), "w", encoding="utf-8") as f:
            f.write(rss(items, name))
    with open(os.path.join(FX, "sources_test.yaml"), "w", encoding="utf-8") as f:
        f.write(f"""sources:
  - {{id: test_gnews_en, name: "Google News", kind: aggregator, gnews: "test", url: "{FX}/gnews_en.xml", lang: en}}
  - {{id: test_gnews_ar, name: "Google News", kind: aggregator, gnews: "test", url: "{FX}/gnews_ar.xml", lang: ar}}
  - {{id: test_opinion,  name: "Test Opinion Desk", kind: opinion, url: "{FX}/opinion.xml", lang: en, category: opinion}}
  - {{id: test_broken,   name: "Broken", kind: media, url: "{FX}/missing.xml", lang: en}}
""")
    print(f"fixtures: {len(gn)} en items, {len(gn_ar)} ar items, {len(opinion)} opinion → {FX}")


if __name__ == "__main__":
    main()
