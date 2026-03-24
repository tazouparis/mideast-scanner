#!/usr/bin/env python3
"""
MidEast Intel Scanner — Version Serveur (sans GUI)
Tourne sur GitHub Actions toutes les 5 minutes, 24h/24.
Envoie les alertes WhatsApp via CallMeBot.
"""
import os, json, re, subprocess, urllib.parse, urllib.request
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional

# ── Config depuis variables d'environnement (GitHub Secrets) ──
WA_PHONE   = os.environ.get('WA_PHONE',  '').strip().replace('+', '')
WA_APIKEY  = os.environ.get('WA_APIKEY', '').strip()
SEUIL      = int(os.environ.get('SEUIL_NIVEAU', '2'))
STATE_FILE = 'state.json'

# ── Sources RSS ────────────────────────────────────────────────
SOURCES = [
    {'nom': 'Al Jazeera',      'url': 'https://www.aljazeera.com/xml/rss/all.xml'},
    {'nom': 'BBC Monde',       'url': 'https://feeds.bbci.co.uk/news/world/rss.xml'},
    {'nom': 'Reuters',         'url': 'https://feeds.reuters.com/reuters/worldNews'},
    {'nom': 'Times of Israel', 'url': 'https://www.timesofisrael.com/feed/'},
    {'nom': 'The Guardian',    'url': 'https://www.theguardian.com/world/rss'},
    {'nom': 'Middle East Eye', 'url': 'https://www.middleeasteye.net/rss'},
    {'nom': 'Aviation Herald', 'url': 'https://avherald.com/h?page=&opt=0'},
    {'nom': 'FlightGlobal',    'url': 'https://www.flightglobal.com/rss/news.xml'},
]

# ── Mots-clés de filtrage ──────────────────────────────────────
MOTS_CRITIQUES = [
    'war declared','guerre déclarée','nuclear strike','frappe nucléaire',
    'missile attack','ballistic missile','hypersonic','attack on israel',
    'attack on iran','iran strike','israel strike','us strike','airstrike',
    'frappe aérienne','no-fly zone','zone d\'exclusion','strait of hormuz',
    'détroit d\'ormuz','oil embargo','embargo pétrolier','world war',
    'troisième guerre','third world war',
]
MOTS_ALERTES = [
    'iran','israel','hamas','hezbollah','houthi','gaza','west bank',
    'trump','middle east','moyen-orient','saudi arabia','arabie saoudite',
    'dubai','abu dhabi','doha','qatar','yemen','syria','syrie','iraq','irak',
    'lebanon','liban','nuclear','nucléaire','missile','drone attack',
    'warship','military','militaire','ceasefire','cessez-le-feu',
    'hostage','otage','sanctions','oil','pétrole','gulf','golfe',
]
MOTS_AVIATION = [
    'dubai airport','abu dhabi airport','doha airport','riyadh airport',
    'jeddah airport','kuwait airport','bahrain airport','muscat airport',
    'dxb','auh','doh','ruh','jed','kwi','bah','mct',
    'emirates airline','etihad airways','qatar airways','flydubai',
    'airspace closed','no-fly zone','notam','flight ban','airspace restricted',
    'airport closed','runway','evacuation flight','diverted to',
    'drone hit','missile near airport','airport attack',
]
MOTS_REGION = [
    'dubai','abu dhabi','doha','riyadh','tehran','beirut','baghdad',
    'gulf','iran','israel','saudi','kuwait','bahrain','oman','qatar',
    'karachi','istanbul','kabul',
]

@dataclass
class Article:
    id:      str
    titre:   str
    lien:    str
    source:  str
    date:    datetime
    niveau:  int   # 0=info 1=alerte 2=critique
    tags:    List[str] = field(default_factory=list)
    aviation: bool = False

# ── Détection aviation ─────────────────────────────────────────
def est_aviation(texte: str) -> bool:
    t = texte.lower()
    if any(kw in t for kw in MOTS_AVIATION):
        return True
    generiques = ['airport','airline','aircraft','flight','airspace','runway','terminal']
    nb = sum(1 for kw in generiques if kw in t)
    return nb >= 2 and any(r in t for r in MOTS_REGION)

# ── Niveau de l'article ────────────────────────────────────────
def calculer_niveau(texte: str) -> int:
    t = texte.lower()
    if any(kw in t for kw in MOTS_CRITIQUES):
        return 2
    if any(kw in t for kw in MOTS_ALERTES):
        return 1
    return 0

# ── Tags ───────────────────────────────────────────────────────
TAGS_MAP = {
    'iran':['iran','iranian'],'israel':['israel','israeli'],
    'hamas':['hamas'],'hezbollah':['hezbollah'],
    'houthi':['houthi','yemen'],'gaza':['gaza'],
    'saudi':['saudi','riyadh','jeddah'],'gulf':['gulf','golfe'],
    'aeroport':['airport','airspace','airline','dxb','doh','auh'],
    'nucleaire':['nuclear','nucléaire'],'conflit':['war','conflict','strike','attack','ceasefire'],
}
def calculer_tags(texte: str) -> List[str]:
    t = texte.lower()
    return [tag for tag, mots in TAGS_MAP.items() if any(m in t for m in mots)][:5]

# ── Parser un article RSS ─────────────────────────────────────
def parser_article(entree, source_nom: str) -> Optional[Article]:
    try:
        titre = entree.get('title', '').strip()
        lien  = entree.get('link',  '').strip()
        desc  = re.sub(r'<[^>]+>', '', entree.get('summary', ''))
        texte = f'{titre} {desc}'.lower()

        niveau = calculer_niveau(texte)
        if niveau == 0:
            return None  # pas pertinent

        # Date de publication
        published = entree.get('published_parsed') or entree.get('updated_parsed')
        if published:
            import time
            date = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)
        else:
            date = datetime.now(tz=timezone.utc)

        art_id = lien or f'{titre[:40]}{source_nom}'
        tags   = calculer_tags(texte)
        if est_aviation(texte) and 'aeroport' not in tags:
            tags.insert(0, 'aeroport')

        return Article(
            id=art_id, titre=titre, lien=lien,
            source=source_nom, date=date,
            niveau=niveau, tags=tags,
            aviation='aeroport' in tags,
        )
    except Exception:
        return None

# ── Récupération des flux RSS ─────────────────────────────────
def recuperer_articles() -> List[Article]:
    try:
        import feedparser
    except ImportError:
        subprocess.run(['pip', 'install', 'feedparser', '-q'], check=False)
        import feedparser

    articles = []
    for src in SOURCES:
        try:
            flux = feedparser.parse(src['url'])
            for e in flux.entries[:30]:
                art = parser_article(e, src['nom'])
                if art:
                    articles.append(art)
            print(f'  ✓ {src["nom"]} — {len(flux.entries)} entrées')
        except Exception as ex:
            print(f'  ✗ {src["nom"]} — {ex}')
    return articles

# ── Chargement/sauvegarde de l'état ───────────────────────────
def charger_etat() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {'envoyes': [], 'last_scan': ''}

def sauvegarder_etat(etat: dict):
    # Garder seulement les 500 derniers IDs pour ne pas grossir indéfiniment
    etat['envoyes'] = etat['envoyes'][-500:]
    etat['last_scan'] = datetime.now(tz=timezone.utc).isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(etat, f, indent=2)

# ── Envoi WhatsApp ────────────────────────────────────────────
def envoyer_whatsapp(phone: str, apikey: str, message: str) -> bool:
    try:
        texte    = message.strip()
        text_enc = urllib.parse.quote_plus(texte)
        url = f'https://api.callmebot.com/whatsapp.php?phone={phone}&text={text_enc}&apikey={apikey}'
        result = subprocess.run(
            ['curl', '-s', '-L', '--max-time', '20', url],
            capture_output=True, text=True, timeout=25
        )
        corps = result.stdout
        print(f'  [WA] {corps[:120].strip()}')
        return result.returncode == 0 and 'APIKey is invalid' not in corps
    except Exception as e:
        print(f'  [WA] Erreur : {e}')
        return False

# ── Formatage du message ──────────────────────────────────────
NIVEAUX_LABEL = {0: 'INFO', 1: 'ALERTE', 2: 'CRITIQUE'}
NIVEAUX_ICONE = {0: 'i', 1: '!', 2: '!!'}

def formater_message(article: Article) -> str:
    icone = '✈️' if article.aviation else '📡'
    niv   = NIVEAUX_LABEL.get(article.niveau, 'ALERTE')
    tags  = ' | '.join(article.tags[:3]).upper() if article.tags else ''
    return (
        f"{icone} *MidEast Scanner* [{niv}]\n"
        f"{article.titre}\n"
        f"Source: {article.source}\n"
        f"{tags}\n"
        f"{article.date.strftime('%d/%m %H:%M')} UTC\n"
        f"{article.lien}"
    )

# ── Programme principal ───────────────────────────────────────
def main():
    print(f'\n=== MidEast Scanner — {datetime.now(tz=timezone.utc).strftime("%d/%m/%Y %H:%M")} UTC ===\n')

    if not WA_PHONE or not WA_APIKEY:
        print('ERREUR : Variables WA_PHONE et WA_APIKEY manquantes.')
        print('→ Ajoute-les dans Settings > Secrets > Actions de ton repo GitHub.')
        return

    print(f'Config : phone={WA_PHONE}  seuil={SEUIL}')
    print(f'\nRécupération des flux RSS...')
    articles = recuperer_articles()
    print(f'\n→ {len(articles)} articles pertinents trouvés')

    etat = charger_etat()
    deja_envoyes = set(etat.get('envoyes', []))

    # Filtrer : niveau >= seuil, pas encore envoyé, max 5 min de retard accepté
    a_envoyer = [
        a for a in articles
        if a.niveau >= SEUIL and a.id not in deja_envoyes
    ]

    # Trier : aviation d'abord, puis par niveau décroissant
    a_envoyer.sort(key=lambda x: (not x.aviation, -x.niveau, x.date))

    # Limiter à 5 messages par cycle pour ne pas spammer
    a_envoyer = a_envoyer[:5]

    print(f'\n→ {len(a_envoyer)} nouvelles alertes à envoyer\n')

    nb_envoyes = 0
    for art in a_envoyer:
        print(f'  Envoi : [{NIVEAUX_LABEL[art.niveau]}] {art.titre[:60]}…')
        msg = formater_message(art)
        ok  = envoyer_whatsapp(WA_PHONE, WA_APIKEY, msg)
        if ok:
            deja_envoyes.add(art.id)
            nb_envoyes += 1
            print(f'  ✓ Envoyé')
        else:
            print(f'  ✗ Échec')

    etat['envoyes'] = list(deja_envoyes)
    sauvegarder_etat(etat)

    print(f'\n=== Terminé : {nb_envoyes} message(s) envoyé(s) ===\n')

if __name__ == '__main__':
    main()
