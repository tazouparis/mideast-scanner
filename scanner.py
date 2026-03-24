#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════╗
║   MidEast Intel Scanner — Application Mac        ║
║   Interface 100 % française                      ║
║   pip3 install PyQt6 feedparser                  ║
╚══════════════════════════════════════════════════╝
"""
import sys, os, re, csv, subprocess, webbrowser, json, math
import urllib.request, urllib.parse, threading
import xml.etree.ElementTree as ET
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict

# ── Installation automatique des dépendances ──────────────────
def _installer(pkg):
    try:
        __import__(pkg.split('[')[0].replace('-', '_'))
    except ImportError:
        print(f"  → Installation de {pkg}…")
        # Essai 1 : avec --break-system-packages (Python système)
        r = subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '-q',
                            '--break-system-packages'], capture_output=True)
        if r.returncode != 0:
            # Essai 2 : sans le flag (Xcode Python / venv)
            subprocess.run([sys.executable, '-m', 'pip', 'install', pkg, '-q'],
                           check=False)

_installer('feedparser')
_installer('PyQt6')

import feedparser
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea, QFrame,
    QSizePolicy, QSystemTrayIcon, QMenu, QFileDialog,
    QMessageBox, QCheckBox, QDialog, QFormLayout, QDialogButtonBox,
    QTabWidget, QTextEdit,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QAction,
)

# ══════════════════════════════════════════════════════════════
#  THÈME COULEURS
# ══════════════════════════════════════════════════════════════
C = {
    'bg':       '#0d0f14',
    'surface':  '#141720',
    'card':     '#1a1f2e',
    'border':   '#252b3b',
    'accent':   '#f97316',
    'rouge':    '#ef4444',
    'bleu':     '#3b82f6',
    'vert':     '#22c55e',
    'jaune':    '#eab308',
    'violet':   '#8b5cf6',
    'cyan':     '#06b6d4',   # couleur Aviation
    'texte':    '#e2e8f0',
    'discret':  '#64748b',
    'info':     '#3b82f6',
    'alerte':   '#eab308',
    'critique': '#ef4444',
}

STYLE_GLOBAL = f"""
* {{
    font-family: -apple-system, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
}}
QMainWindow, QWidget#root, QWidget#gauche, QWidget#centre, QWidget#droite {{
    background: {C['bg']};  color: {C['texte']};
}}
QScrollArea   {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 5px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {C['border']}; border-radius: 2px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QLineEdit {{
    background: {C['card']}; border: 1px solid {C['border']};
    border-radius: 8px; color: {C['texte']};
    padding: 7px 12px; font-size: 12px;
}}
QLineEdit:focus {{ border-color: {C['accent']}; }}
QTextEdit {{
    background: {C['card']}; border: 1px solid {C['border']};
    border-radius: 8px; color: {C['texte']}; font-size: 12px;
}}
QDialog, QTabWidget::pane {{
    background: {C['surface']}; color: {C['texte']};
}}
QTabBar::tab {{
    background: {C['card']}; color: {C['discret']};
    padding: 8px 16px; border-radius: 6px; margin-right: 4px;
    font-size: 12px;
}}
QTabBar::tab:selected {{ background: {C['accent']}22; color: {C['accent']}; }}
QMenu {{
    background: {C['surface']}; border: 1px solid {C['border']};
    border-radius: 10px; padding: 5px; color: {C['texte']};
}}
QMenu::item {{ padding: 7px 20px; border-radius: 5px; font-size: 13px; }}
QMenu::item:selected {{ background: {C['card']}; color: {C['accent']}; }}
QMenu::separator {{ background: {C['border']}; height: 1px; margin: 3px 8px; }}
QToolTip {{
    background: {C['surface']}; color: {C['texte']};
    border: 1px solid {C['border']}; border-radius: 5px; padding: 4px 8px;
}}
QCheckBox {{ color: {C['texte']}; font-size: 12px; spacing: 6px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {C['border']}; border-radius: 3px;
    background: {C['card']};
}}
QCheckBox::indicator:checked {{
    background: {C['accent']}; border-color: {C['accent']};
}}
QMessageBox {{ background: {C['surface']}; color: {C['texte']}; }}
QDialogButtonBox QPushButton {{
    background: {C['card']}; color: {C['texte']};
    border: 1px solid {C['border']}; border-radius: 7px;
    padding: 7px 18px; font-size: 12px;
}}
QDialogButtonBox QPushButton:hover {{
    border-color: {C['accent']}; color: {C['accent']};
}}
"""

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════
INTERVALLE_PAR_DEFAUT = 120
INTERVALLES = {'1 min': 60, '3 min': 180, '1 heure': 3600}
NOTIF_CONFIG_FILE = os.path.expanduser('~/.mideast_scanner_config.json')

SOURCES = [
    {'nom': 'Al Jazeera',    'couleur': C['rouge'],  'url': 'https://www.aljazeera.com/xml/rss/all.xml'},
    {'nom': 'BBC Monde',     'couleur': C['bleu'],   'url': 'https://feeds.bbci.co.uk/news/world/rss.xml'},
    {'nom': 'Reuters',       'couleur': C['accent'], 'url': 'https://feeds.reuters.com/reuters/worldNews'},
    {'nom': 'France 24',     'couleur': C['violet'], 'url': 'https://www.france24.com/en/rss'},
    {'nom': 'The Guardian',  'couleur': C['vert'],   'url': 'https://www.theguardian.com/world/rss'},
    {'nom': 'AP News',       'couleur': C['jaune'],  'url': 'https://feeds.apnews.com/rss/apf-intlnews'},
    {'nom': 'Aviation Herald','couleur': C['cyan'],  'url': 'https://avherald.com/h?page=&opt=0'},
    {'nom': 'FlightGlobal',  'couleur': C['cyan'],   'url': 'https://www.flightglobal.com/rss/news.xml'},
]

# Filtres — Aviation EN PREMIER
FILTRES = [
    ('aeroport', '✈️', 'Aéroports & Aviation'),      # ← EN PREMIER
    ('tout',     '🌍', 'Tout le Moyen-Orient'),
    ('iran',     '🇮🇷', 'Iran'),
    ('trump',    '🇺🇸', 'USA / Trump'),
    ('israel',   '🇮🇱', 'Israël / Gaza'),
    ('golfe',    '🏙️',  'Golfe / Dubaï'),
    ('conflit',  '⚔️',  'Conflits actifs'),
    ('breaking', '🔴',  'Breaking News'),
]


# ── Mots-clés Aviation : TIER 1 = haute confiance (1 suffit)
# ── TIER 2 = génériques (2 requis pour tagger aviation)
AVIATION_TIER1 = [
    # Noms complets d'aéroports — Golfe
    'dubai airport', 'dubai international airport', 'al maktoum airport',
    'abu dhabi airport', 'zayed international airport',
    'doha airport', 'hamad international airport',
    'riyadh airport', 'king khalid international',
    'jeddah airport', 'king abdulaziz international',
    'kuwait international airport',
    'bahrain international airport',
    'muscat international airport',
    'sharjah international airport',
    'ras al khaimah airport',
    # Noms complets — Asie / Moyen-Orient
    'karachi airport', 'jinnah international airport',
    'islamabad airport', 'new islamabad airport',
    'tehran airport', 'imam khomeini airport', 'mehrabad airport',
    'beirut airport', 'rafic hariri airport',
    'baghdad international airport',
    'istanbul airport', 'new istanbul airport', 'ataturk airport',
    'kabul airport', 'hamid karzai airport',
    'amman airport', 'queen alia airport',
    'tel aviv airport', 'ben gurion airport',
    'cairo international airport',
    'mumbai airport', 'chhatrapati shivaji airport',
    'delhi airport', 'indira gandhi airport',
    'singapore changi', 'changi airport',
    'colombo airport', 'bandaranaike airport',
    # Compagnies aériennes — noms complets
    'emirates airline', 'emirates airlines', 'emirates flight',
    'etihad airways', 'etihad airlines', 'etihad flight',
    'qatar airways', 'qatar airlines', 'qatar flight',
    'flydubai', 'fly dubai',
    'air arabia', 'air arabia flight',
    'saudia airlines', 'saudi arabian airlines', 'saudia flight',
    'kuwait airways',
    'oman air', 'oman air flight',
    'gulf air', 'gulf air flight',
    'jazeera airways', 'flydeal',
    'flynas', 'air india flight', 'indigo flight',
    # Événements spécifiques aviation
    'no-fly zone', 'airspace closure', 'airspace closed',
    'airspace violation', 'airspace banned', 'airspace blocked',
    'flight ban', 'flight restriction imposed', 'flights suspended',
    'flights cancelled over', 'flights diverted', 'aircraft diverted',
    'plane diverted', 'flight diverted',
    'airport closed', 'airport shutdown', 'airport attack',
    'airport evacuation', 'airport bombing', 'airport seized',
    'missile near airport', 'drone over airport', 'drone at airport',
    'airport hit', 'explosion at airport', 'attack on airport',
    'notam issued', 'notam declared',
    'civil aviation authority', 'air traffic control closed',
    'intercept aircraft', 'fighter jets scrambled',
    'aircraft intercepted', 'warplane',
    'strait of hormuz closure', 'hormuz airspace',
]

AVIATION_TIER2 = [
    'airport', 'airspace', 'aviation', 'airline',
    'air traffic', 'flight ban', 'runway', 'civil aviation',
]

MOTS_CLES = {
    # ── AVIATION — liste combinée (utilisée pour TOUS_MOTS)
    # Le tag aviation réel est calculé via _est_aviation() ci-dessous
    'aeroport': AVIATION_TIER1 + AVIATION_TIER2,
    # ── RÉGIONS ──────────────────────────────────────────────
    'iran':    ['iran','iranian','tehran','khamenei','nuclear','irgc','ayatollah','isfahan'],
    'trump':   ['trump','united states','washington','pentagon','white house','us military','american'],
    'israel':  ['israel','israeli','netanyahu','gaza','hamas','idf','tel aviv','jerusalem',
                'west bank','hezbollah','rafah','ceasefire','settler'],
    'golfe':   ['dubai','uae','saudi arabia','riyadh','abu dhabi','qatar','doha',
                'kuwait','bahrain','oman','gulf','aramco'],
    'conflit': ['war','strike','attack','missile','bomb','explosion','troops','airstrike',
                'nuclear threat','sanction','drone strike','killed','battle','offensive'],
}

MOTS_BREAKING = [
    'killed', 'explosion', 'attack', 'missile strike', 'declares war',
    'nuclear', 'ceasefire broken', 'invasion', 'assassinated', 'bombed',
    'airstrike', 'war declared', 'coup', 'emergency',
    # Breaking aviation spécifique
    'airport closed', 'airspace closed', 'airport attack', 'flight emergency',
    'no-fly zone declared', 'airport evacuation', 'missile near airport',
]

TOUS_MOTS = list({kw for kws in MOTS_CLES.values() for kw in kws})
MOTS_CLES_TOP = [
    'airport', 'airspace', 'iran', 'trump', 'israel', 'gaza', 'nuclear', 'war',
    'missile', 'dubai', 'saudi', 'hamas', 'ceasefire', 'drone', 'hezbollah',
    'emirates', 'qatar airways', 'no-fly',
]
ETIQUETTES_TAGS = {
    'aeroport': '✈️ Aviation', 'iran': '🇮🇷 Iran', 'trump': '🇺🇸 USA',
    'israel': '🇮🇱 Israël', 'golfe': '🏙️ Golfe', 'conflit': '⚔️ Conflit',
}
NIVEAUX = {
    0: ('ℹ️', C['info'],     'Info'),
    1: ('⚠️', C['alerte'],   'Alerte'),
    2: ('🔴', C['critique'], 'Critique'),
}

# ══════════════════════════════════════════════════════════════
#  MODÈLE DE DONNÉES
# ══════════════════════════════════════════════════════════════
@dataclass
class Article:
    id:         str
    titre:      str
    desc:       str
    lien:       str
    date:       datetime
    source:     str
    couleur:    str
    tags:       List[str] = field(default_factory=list)
    breaking:   bool = False
    texte:      str  = ''
    niveau:     int  = 0
    priorite:   int  = 0   # 0=normal, 1=aviation → sort first

def _est_aviation(texte: str) -> bool:
    """Logique stricte à 2 niveaux — évite les faux positifs.
    TIER 1 : noms complets d'aéroports, compagnies, événements précis → 1 seul suffit.
    TIER 2 : mots génériques → 2 requis ensemble.
    """
    # Tier 1 : haute confiance, 1 seul suffit
    if any(kw in texte for kw in AVIATION_TIER1):
        return True
    # Tier 2 : générique, seulement si 2+ mots présents ET un mot régional
    mots_region = ['dubai', 'abu dhabi', 'doha', 'riyadh', 'tehran', 'beirut',
                   'baghdad', 'gulf', 'iran', 'israel', 'saudi', 'kuwait',
                   'bahrain', 'oman', 'qatar', 'karachi', 'istanbul', 'kabul']
    tier2_count = sum(1 for kw in AVIATION_TIER2 if kw in texte)
    region_match = any(r in texte for r in mots_region)
    return tier2_count >= 2 and region_match

def _analyser_niveau(texte: str, tags: List[str], breaking: bool) -> int:
    if breaking:
        return 2
    mots_alerte = ['sanction', 'threat', 'nuclear', 'military', 'troops',
                   'missile', 'hezbollah', 'hamas', 'no-fly zone',
                   'airspace closure', 'airport closed', 'flights suspended']
    if any(m in texte for m in mots_alerte) or len(tags) >= 2:
        return 1
    return 0

def _analyser_entree(entree: dict, src: dict) -> Optional[Article]:
    try:
        titre = entree.get('title', '').strip()
        if not titre:
            return None
        desc_brute = entree.get('summary', entree.get('description', ''))
        desc  = re.sub(r'<[^>]+>', '', desc_brute).strip()
        lien  = entree.get('link', '')
        pub   = entree.get('published_parsed') or entree.get('updated_parsed')
        date  = datetime(*pub[:6]) if pub else datetime.now()
        texte = (titre + ' ' + desc).lower()
        if not any(kw in texte for kw in TOUS_MOTS):
            return None

        # Tags régionaux normaux
        tags_regionaux = [
            cat for cat, kws in MOTS_CLES.items()
            if cat != 'aeroport' and any(kw in texte for kw in kws)
        ]
        # Tag aviation : logique stricte à 2 niveaux
        tags = (['aeroport'] if _est_aviation(texte) else []) + tags_regionaux

        # Un article doit avoir au moins un tag pour être gardé
        if not tags:
            return None

        breaking = any(bw in texte for bw in MOTS_BREAKING)
        niveau   = _analyser_niveau(texte, tags, breaking)
        priorite = 1 if 'aeroport' in tags else 0
        return Article(
            id=lien or titre, titre=titre, desc=desc[:280], lien=lien,
            date=date, source=src['nom'], couleur=src['couleur'],
            tags=tags, breaking=breaking, texte=texte,
            niveau=niveau, priorite=priorite,
        )
    except Exception:
        return None

def _temps_ecoule(dt: datetime) -> str:
    diff = (datetime.now() - dt).total_seconds()
    if diff < 60:    return f'{int(diff)}s'
    if diff < 3600:  return f'{int(diff/60)} min'
    if diff < 86400: return f'{int(diff/3600)} h'
    return f'{int(diff/86400)} j'

# ══════════════════════════════════════════════════════════════
#  NOTIFICATIONS — WHATSAPP (CallMeBot) + TELEGRAM
# ══════════════════════════════════════════════════════════════
def _charger_config_xml() -> dict:
    """Lit config.xml situé dans le même dossier que scanner.py."""
    cfg = {}
    try:
        xml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.xml')
        if not os.path.exists(xml_path):
            return cfg
        tree = ET.parse(xml_path)
        root = tree.getroot()
        notif = root.find('notifications')
        if notif is None:
            return cfg
        wa = notif.find('whatsapp')
        if wa is not None:
            cfg['wa_phone']  = (wa.findtext('phone')  or '').strip()
            cfg['wa_apikey'] = (wa.findtext('apikey') or '').strip()
            cfg['wa_actif']  = (wa.findtext('active') or 'false').strip().lower() == 'true'
        tg = notif.find('telegram')
        if tg is not None:
            cfg['tg_chat_id'] = (tg.findtext('chat_id') or '').strip()
            cfg['tg_token']   = (tg.findtext('token')   or '').strip()
            cfg['tg_actif']   = (tg.findtext('active')  or 'false').strip().lower() == 'true'
        seuil = notif.findtext('seuil_niveau')
        if seuil:
            cfg['seuil_niveau'] = int(seuil.strip())
    except Exception:
        pass
    return cfg

def _charger_config() -> dict:
    defaults = {
        'wa_phone': '', 'wa_apikey': '', 'wa_actif': False,
        'tg_chat_id': '', 'tg_token': '', 'tg_actif': False,
        'seuil_niveau': 2,
    }
    # 1. JSON sauvegardé (préférences utilisateur)
    try:
        if os.path.exists(NOTIF_CONFIG_FILE):
            with open(NOTIF_CONFIG_FILE, 'r') as f:
                saved = json.load(f)
            defaults.update(saved)
    except Exception:
        pass
    # 2. XML écrase TOUJOURS les credentials (source de vérité)
    xml = _charger_config_xml()
    for cle in ('wa_phone', 'wa_apikey', 'wa_actif', 'tg_chat_id', 'tg_token', 'tg_actif'):
        if xml.get(cle):   # n'écrase que si la valeur XML est non-vide
            defaults[cle] = xml[cle]
    return defaults

def _sauvegarder_config(cfg: dict):
    try:
        with open(NOTIF_CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def _envoyer_whatsapp(phone: str, apikey: str, message: str) -> tuple[bool, str]:
    """Envoie via CallMeBot — curl système, identique à un navigateur."""
    try:
        phone  = phone.strip().replace('+', '').replace(' ', '')
        apikey = apikey.strip().replace(' ', '')
        texte  = ''.join(c for c in message if ord(c) < 128).strip() or 'Test'
        text_enc = urllib.parse.quote_plus(texte)
        url = (f'https://api.callmebot.com/whatsapp.php'
               f'?phone={phone}&text={text_enc}&apikey={apikey}')
        print(f'[WA] phone={phone!r} apikey={apikey!r}')
        print(f'[WA] URL → {url}')
        result = subprocess.run(
            ['curl', '-s', '-L', '--max-time', '20', url],
            capture_output=True, text=True, timeout=25
        )
        corps = result.stdout[:300].strip()
        print(f'[WA] Réponse : {corps}')
        if 'APIKey is invalid' in corps:
            return False, 'APIKey invalide — vérifiez le champ API Key'
        if result.returncode == 0 and corps:
            return True, '✓ Message WhatsApp envoyé !'
        return False, f'Erreur curl ({result.returncode})'
    except Exception as e:
        print(f'[WA] Exception : {e}')
        return False, f'Erreur : {str(e)}'

def _envoyer_telegram(chat_id: str, token: str, message: str) -> tuple[bool, str]:
    """Envoie via Telegram Bot API."""
    try:
        params = urllib.parse.urlencode({
            'chat_id':    chat_id,
            'text':       message,
            'parse_mode': 'Markdown',
        })
        url = f'https://api.telegram.org/bot{token}/sendMessage?{params}'
        req = urllib.request.Request(url, headers={'User-Agent': 'MidEastScanner/2.1'})
        with urllib.request.urlopen(req, timeout=10) as r:
            reponse = json.loads(r.read().decode('utf-8', errors='ignore'))
            if reponse.get('ok'):
                return True, '✓ Message Telegram envoyé'
            return False, reponse.get('description', 'Erreur inconnue')
    except Exception as e:
        return False, f'Erreur : {str(e)}'

def _formater_message_alerte(article: Article) -> str:
    icone = NIVEAUX[article.niveau][0]
    tags  = ' | '.join(ETIQUETTES_TAGS.get(t, t) for t in article.tags[:3])
    return (
        f"{icone} *MidEast Scanner — {NIVEAUX[article.niveau][2].upper()}*\n"
        f"📰 *{article.titre}*\n"
        f"🔗 Source : {article.source}\n"
        f"🏷️ {tags}\n"
        f"🕐 {article.date.strftime('%d/%m %H:%M')}\n"
        f"🔗 {article.lien}"
    )

# ══════════════════════════════════════════════════════════════
#  THREAD DE RÉCUPÉRATION
# ══════════════════════════════════════════════════════════════
class WorkerRecup(QThread):
    articles_prets = pyqtSignal(list)
    statut_source  = pyqtSignal(str, bool, int)

    def run(self):
        resultats: List[Article] = []
        for src in SOURCES:
            try:
                flux   = feedparser.parse(src['url'])
                items  = [_analyser_entree(e, src) for e in flux.entries[:40]]
                items  = [a for a in items if a is not None]
                self.statut_source.emit(src['nom'], True, len(items))
                resultats.extend(items)
            except Exception:
                self.statut_source.emit(src['nom'], False, 0)
        self.articles_prets.emit(resultats)

# ══════════════════════════════════════════════════════════════
#  DIALOG NOTIFICATIONS (WhatsApp + Telegram)
# ══════════════════════════════════════════════════════════════
class DialogTelegram(QDialog):
    """Dialog de configuration des notifications — WhatsApp & Telegram."""
    config_sauvegardee = pyqtSignal(dict)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle('⚙️  Notifications — WhatsApp & Telegram')
        self.setFixedSize(560, 620)
        self.setStyleSheet(f'background: {C["surface"]}; color: {C["texte"]};')
        self._cfg = dict(cfg)
        self._construire()

    # ── helpers ──────────────────────────────────────────────
    @staticmethod
    def _hex_to_rgba(hexcol: str, alpha: float) -> str:
        """Convertit #RRGGBB + alpha float → rgba(r,g,b,a) compatible PyQt6."""
        h = hexcol.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'rgba({r},{g},{b},{alpha})'

    def _section_box(self, couleur: str) -> tuple:
        bg  = self._hex_to_rgba(couleur, 0.08)
        brd = self._hex_to_rgba(couleur, 0.35)
        box = QFrame()
        box.setStyleSheet(f'QFrame {{ background: {bg}; border: 1px solid {brd}; border-radius: 10px; }}')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        return box, lay

    def _champ_style(self) -> str:
        return (f'QLineEdit {{ background: {C["card"]}; color: {C["texte"]}; '
                f'border: 1px solid {C["border"]}; border-radius: 6px; '
                f'padding: 6px 10px; font-size: 12px; }}'
                f'QLineEdit:focus {{ border-color: {C["accent"]}; }}')

    def _cb_style(self, couleur: str) -> str:
        """Style propre pour QCheckBox — overrides le stylesheet global."""
        return (f'QCheckBox {{ color: {couleur}; font-size: 12px; font-weight: 600; '
                f'background: transparent; border: none; }}'
                f'QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; '
                f'border: 2px solid {couleur}; background: transparent; }}'
                f'QCheckBox::indicator:checked {{ background: {couleur}; }}')

    def _btn_test_style(self, couleur: str) -> str:
        bg  = self._hex_to_rgba(couleur, 0.12)
        brd = self._hex_to_rgba(couleur, 0.30)
        bgh = self._hex_to_rgba(couleur, 0.22)
        return (f'QPushButton {{ background: {bg}; color: {couleur}; '
                f'border: 1px solid {brd}; border-radius: 8px; '
                f'padding: 7px 14px; font-size: 12px; font-weight: 600; }}'
                f'QPushButton:hover {{ background: {bgh}; }}')

    # ── construction principale ───────────────────────────────
    def _construire(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(22, 20, 22, 16)

        titre = QLabel('🔔  Alertes — Aéroports & Moyen-Orient')
        titre.setStyleSheet(f'color: {C["texte"]}; font-size: 15px; font-weight: 700;')
        lay.addWidget(titre)

        sous = QLabel('Activez WhatsApp et/ou Telegram — vous pouvez utiliser les deux simultanément.')
        sous.setStyleSheet(f'color: {C["discret"]}; font-size: 11px;')
        sous.setWordWrap(True)
        lay.addWidget(sous)

        # ════════ WHATSAPP ════════
        wa_box, wa_lay = self._section_box('#25d366')

        wa_titre_row = QHBoxLayout()
        wa_ic = QLabel('💬'); wa_ic.setStyleSheet('font-size: 18px;')
        wa_titre_row.addWidget(wa_ic)
        wa_t = QLabel('WhatsApp  via CallMeBot')
        wa_t.setStyleSheet(f'color: #25d366; font-size: 13px; font-weight: 700; margin-left:4px;')
        wa_titre_row.addWidget(wa_t)
        wa_titre_row.addStretch()
        self.cb_wa = QCheckBox('Activer')
        self.cb_wa.setChecked(self._cfg.get('wa_actif', False))
        self.cb_wa.setStyleSheet(self._cb_style('#25d366'))
        wa_titre_row.addWidget(self.cb_wa)
        wa_lay.addLayout(wa_titre_row)

        wa_form = QFormLayout(); wa_form.setSpacing(8)
        lbl_s = f'color: {C["discret"]}; font-size: 12px;'

        lbl_phone = QLabel('Numéro (sans +) :'); lbl_phone.setStyleSheet(lbl_s)
        self.champ_wa_phone = QLineEdit(self._cfg.get('wa_phone', ''))
        self.champ_wa_phone.setPlaceholderText('ex : 33673563266')
        self.champ_wa_phone.setStyleSheet(self._champ_style())
        wa_form.addRow(lbl_phone, self.champ_wa_phone)

        lbl_apikey = QLabel('API Key CallMeBot :'); lbl_apikey.setStyleSheet(lbl_s)
        self.champ_wa_apikey = QLineEdit(self._cfg.get('wa_apikey', ''))
        self.champ_wa_apikey.setPlaceholderText('ex : 2764117')
        self.champ_wa_apikey.setStyleSheet(self._champ_style())
        wa_form.addRow(lbl_apikey, self.champ_wa_apikey)
        wa_lay.addLayout(wa_form)

        wa_info = QLabel('① Envoyez "I allow callmebot to send me messages" au +34 644 37 67 94\n'
                         '② Vous recevrez votre apikey par WhatsApp dans quelques secondes.')
        wa_info.setStyleSheet(f'color: {C["discret"]}; font-size: 10px;')
        wa_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        wa_lay.addWidget(wa_info)

        wa_btns = QHBoxLayout(); wa_btns.setSpacing(8)
        self.btn_wa_test = QPushButton('🧪  Tester WhatsApp')
        self.btn_wa_test.setStyleSheet(self._btn_test_style('#25d366'))
        self.btn_wa_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wa_test.clicked.connect(self._tester_wa)
        wa_btns.addWidget(self.btn_wa_test); wa_btns.addStretch()
        self.lbl_wa_res = QLabel('')
        self.lbl_wa_res.setStyleSheet('color: #25d366; font-size: 11px;')
        wa_btns.addWidget(self.lbl_wa_res)
        wa_lay.addLayout(wa_btns)
        lay.addWidget(wa_box)

        # ════════ TELEGRAM ════════
        tg_box, tg_lay = self._section_box(C['bleu'])

        tg_titre_row = QHBoxLayout()
        tg_ic = QLabel('📱'); tg_ic.setStyleSheet('font-size: 18px;')
        tg_titre_row.addWidget(tg_ic)
        tg_t = QLabel('Telegram  Bot API')
        tg_t.setStyleSheet(f'color: {C["bleu"]}; font-size: 13px; font-weight: 700; margin-left:4px;')
        tg_titre_row.addWidget(tg_t)
        tg_titre_row.addStretch()
        self.cb_tg = QCheckBox('Activer')
        self.cb_tg.setChecked(self._cfg.get('tg_actif', False))
        self.cb_tg.setStyleSheet(self._cb_style(C['bleu']))
        tg_titre_row.addWidget(self.cb_tg)
        tg_lay.addLayout(tg_titre_row)

        tg_form = QFormLayout(); tg_form.setSpacing(8)

        lbl_tok = QLabel('Bot Token :'); lbl_tok.setStyleSheet(lbl_s)
        self.champ_tg_token = QLineEdit(self._cfg.get('tg_token', ''))
        self.champ_tg_token.setPlaceholderText('123456789:ABCdefGHIjklMNOpqr…')
        self.champ_tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.champ_tg_token.setStyleSheet(self._champ_style())
        tg_form.addRow(lbl_tok, self.champ_tg_token)

        lbl_cid = QLabel('Chat ID :'); lbl_cid.setStyleSheet(lbl_s)
        self.champ_tg_chatid = QLineEdit(self._cfg.get('tg_chat_id', ''))
        self.champ_tg_chatid.setPlaceholderText('Numéro entier, ex : 123456789')
        self.champ_tg_chatid.setStyleSheet(self._champ_style())
        tg_form.addRow(lbl_cid, self.champ_tg_chatid)
        tg_lay.addLayout(tg_form)

        tg_info = QLabel('① @BotFather → /newbot → copiez le Token\n'
                         '② Ouvrez https://api.telegram.org/bot[TOKEN]/getUpdates pour trouver votre Chat ID')
        tg_info.setStyleSheet(f'color: {C["discret"]}; font-size: 10px;')
        tg_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        tg_lay.addWidget(tg_info)

        tg_btns = QHBoxLayout(); tg_btns.setSpacing(8)
        self.btn_tg_test = QPushButton('🧪  Tester Telegram')
        self.btn_tg_test.setStyleSheet(self._btn_test_style(C['bleu']))
        self.btn_tg_test.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tg_test.clicked.connect(self._tester_tg)
        tg_btns.addWidget(self.btn_tg_test); tg_btns.addStretch()
        self.lbl_tg_res = QLabel('')
        self.lbl_tg_res.setStyleSheet(f'color: {C["bleu"]}; font-size: 11px;')
        tg_btns.addWidget(self.lbl_tg_res)
        tg_lay.addLayout(tg_btns)
        lay.addWidget(tg_box)

        # ════════ SEUIL ════════
        seuil_row = QHBoxLayout(); seuil_row.setSpacing(8)
        seuil_lbl = QLabel('Alerter si niveau ≥')
        seuil_lbl.setStyleSheet(f'color: {C["discret"]}; font-size: 12px;')
        seuil_row.addWidget(seuil_lbl)
        seuil_actuel = self._cfg.get('seuil_niveau', 2)
        self.rb_seuils = {}
        for niv, (icone, couleur, label) in NIVEAUX.items():
            rb = QPushButton(f'{icone} {label}')
            rb.setCheckable(True); rb.setChecked(niv == seuil_actuel)
            bg_chk = self._hex_to_rgba(couleur, 0.13)
            brd_chk = self._hex_to_rgba(couleur, 0.33)
            rb.setStyleSheet(f"""
                QPushButton {{ background: {C['card']}; color: {C['discret']};
                    border: 1px solid {C['border']}; border-radius: 7px;
                    padding: 5px 10px; font-size: 11px; }}
                QPushButton:checked {{ background: {bg_chk}; color: {couleur};
                    border-color: {brd_chk}; }}
            """)
            rb.clicked.connect(lambda checked, n=niv: self._choisir_seuil(n))
            self.rb_seuils[niv] = rb; seuil_row.addWidget(rb)
        seuil_row.addStretch()
        lay.addLayout(seuil_row)

        # ════════ BOUTONS ════════
        btns = QHBoxLayout(); btns.setSpacing(10)
        btn_ann = QPushButton('Annuler')
        btn_ann.setStyleSheet(f"""
            QPushButton {{ background: {C['card']}; color: {C['discret']};
                border: 1px solid {C['border']}; border-radius: 8px; padding: 9px 16px; }}
        """)
        btn_ann.clicked.connect(self.reject)
        btns.addStretch(); btns.addWidget(btn_ann)

        btn_sauv = QPushButton('✓  Sauvegarder')
        btn_sauv.setStyleSheet(f"""
            QPushButton {{ background: {C['accent']}22; color: {C['accent']};
                border: 1px solid {C['accent']}44; border-radius: 8px;
                padding: 9px 20px; font-size: 13px; font-weight: 700; }}
            QPushButton:hover {{ background: {C['accent']}35; }}
        """)
        btn_sauv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_sauv.clicked.connect(self._sauvegarder)
        btns.addWidget(btn_sauv)
        lay.addLayout(btns)

    # ── logique ──────────────────────────────────────────────
    def _choisir_seuil(self, niv: int):
        self._cfg['seuil_niveau'] = niv
        for n, rb in self.rb_seuils.items():
            rb.setChecked(n == niv)

    def _lire_champs(self):
        self._cfg['wa_phone']   = self.champ_wa_phone.text().strip().replace('+', '')
        self._cfg['wa_apikey']  = self.champ_wa_apikey.text().strip()
        self._cfg['wa_actif']   = self.cb_wa.isChecked()
        self._cfg['tg_token']   = self.champ_tg_token.text().strip()
        self._cfg['tg_chat_id'] = self.champ_tg_chatid.text().strip()
        self._cfg['tg_actif']   = self.cb_tg.isChecked()

    def _tester_wa(self):
        self._lire_champs()
        phone  = self._cfg.get('wa_phone', '')
        apikey = self._cfg.get('wa_apikey', '')
        if not phone or not apikey:
            self.lbl_wa_res.setStyleSheet(f'color: {C["rouge"]}; font-size: 11px;')
            self.lbl_wa_res.setText('⚠️ Remplissez Numéro + API Key')
            return
        self.lbl_wa_res.setStyleSheet('color: #25d366; font-size: 11px;')
        self.lbl_wa_res.setText('⏳ Envoi…')
        def _run():
            ok, detail = _envoyer_whatsapp(phone, apikey,
                'ALERTE MIDEAST SCANNER - Systeme de surveillance actif. '
                'Vous recevrez desormais les alertes critiques sur ce numero.')
            self._wa_test_res = (ok, detail)
        threading.Thread(target=_run, daemon=True).start()
        QTimer.singleShot(6000, self._afficher_wa)

    def _afficher_wa(self):
        res = getattr(self, '_wa_test_res', None)
        if res is None:
            self.lbl_wa_res.setText('⏳ En attente…'); return
        ok, detail = res
        self.lbl_wa_res.setStyleSheet(
            f'color: {"#25d366" if ok else C["rouge"]}; font-size: 11px;')
        self.lbl_wa_res.setText(f'{"✓" if ok else "✗"} {detail}')

    def _tester_tg(self):
        self._lire_champs()
        token   = self._cfg.get('tg_token', '')
        chat_id = self._cfg.get('tg_chat_id', '')
        if not token or not chat_id:
            self.lbl_tg_res.setStyleSheet(f'color: {C["rouge"]}; font-size: 11px;')
            self.lbl_tg_res.setText('⚠️ Remplissez Token + Chat ID')
            return
        self.lbl_tg_res.setStyleSheet(f'color: {C["bleu"]}; font-size: 11px;')
        self.lbl_tg_res.setText('⏳ Envoi…')
        def _run():
            ok, detail = _envoyer_telegram(chat_id, token,
                '✈️ *MidEast Scanner TEST* — Telegram opérationnel !')
            self._tg_test_res = (ok, detail)
        threading.Thread(target=_run, daemon=True).start()
        QTimer.singleShot(5000, self._afficher_tg)

    def _afficher_tg(self):
        res = getattr(self, '_tg_test_res', None)
        if res is None:
            self.lbl_tg_res.setText('⏳ En attente…'); return
        ok, detail = res
        self.lbl_tg_res.setStyleSheet(
            f'color: {C["vert"] if ok else C["rouge"]}; font-size: 11px;')
        self.lbl_tg_res.setText(f'{"✓" if ok else "✗"} {detail}')

    def _sauvegarder(self):
        self._lire_champs()
        _sauvegarder_config(self._cfg)
        self.config_sauvegardee.emit(self._cfg)
        self.accept()

# ══════════════════════════════════════════════════════════════
#  COMPOSANTS UI — CARTE ARTICLE
# ══════════════════════════════════════════════════════════════
class CarteArticle(QFrame):
    def __init__(self, article: Article, parent=None):
        super().__init__(parent)
        self._lien = article.lien
        self._construire(article)

    def _construire(self, a: Article):
        icone_niv, couleur_niv, _ = NIVEAUX[a.niveau]
        # Aviation → bordure cyan distincte
        if 'aeroport' in a.tags:
            couleur_bord = C['cyan']
            fond_gauche  = C['cyan']
        else:
            couleur_bord = couleur_niv if a.niveau > 0 else C['border']
            fond_gauche  = couleur_niv

        self.setStyleSheet(f"""
            CarteArticle {{
                background: {C['card']};
                border: 1px solid {couleur_bord}55;
                border-left: 3px solid {fond_gauche};
                border-radius: 10px;
            }}
            CarteArticle:hover {{
                background: #1e2435;
                border-left-color: {C['accent']};
            }}
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(6)

        # ── Ligne méta ──
        meta = QHBoxLayout()
        meta.setSpacing(6)

        # Badge source
        src_l = QLabel(a.source)
        src_l.setStyleSheet(f"""
            QLabel {{ background: {a.couleur}22; color: {a.couleur};
                      border: 1px solid {a.couleur}55; border-radius: 4px;
                      padding: 1px 8px; font-size: 10px; font-weight: 700; }}
        """)
        meta.addWidget(src_l)

        # Badge niveau
        niv_l = QLabel(f'{icone_niv} {NIVEAUX[a.niveau][2].upper()}')
        niv_l.setStyleSheet(f"""
            QLabel {{ background: {couleur_niv}22; color: {couleur_niv};
                      border: 1px solid {couleur_niv}44; border-radius: 4px;
                      padding: 1px 8px; font-size: 10px; font-weight: 700; }}
        """)
        meta.addWidget(niv_l)

        # Tags (max 3)
        for tag in a.tags[:3]:
            tl = QLabel(ETIQUETTES_TAGS.get(tag, tag))
            tl.setStyleSheet(f"""
                QLabel {{ color: {C['discret']}; border: 1px solid {C['border']};
                          border-radius: 4px; padding: 1px 7px; font-size: 10px; }}
            """)
            meta.addWidget(tl)

        meta.addStretch()
        tl = QLabel(_temps_ecoule(a.date))
        tl.setStyleSheet(f'color: {C["discret"]}; font-size: 11px;')
        meta.addWidget(tl)
        lay.addLayout(meta)

        # Titre
        titre_l = QLabel(a.titre)
        titre_l.setStyleSheet(f'color: {C["texte"]}; font-size: 13px; font-weight: 600;')
        titre_l.setWordWrap(True)
        lay.addWidget(titre_l)

        # Description
        if a.desc:
            court = a.desc[:190] + ('…' if len(a.desc) > 190 else '')
            dl = QLabel(court)
            dl.setStyleSheet(f'color: {C["discret"]}; font-size: 11px;')
            dl.setWordWrap(True)
            lay.addWidget(dl)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._lien:
            webbrowser.open(self._lien)
        super().mousePressEvent(e)


# ══════════════════════════════════════════════════════════════
#  BOUTON FILTRE
# ══════════════════════════════════════════════════════════════
class BoutonFiltre(QPushButton):
    def __init__(self, fid: str, icone: str, etiquette: str, parent=None):
        super().__init__(parent)
        self.fid = fid
        self._icone = icone
        self._etiquette = etiquette
        self._compteur = 0
        self._actif = False
        self._rendu()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _rendu(self):
        n = f'  {self._compteur}' if self._compteur else ''
        self.setText(f'{self._icone}  {self._etiquette}{n}')
        couleur = C['cyan'] if self.fid == 'aeroport' else C['accent']
        if self._actif:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {couleur}22; color: {couleur};
                    border: 1px solid {couleur}44; border-radius: 8px;
                    padding: 9px 12px; font-size: 13px; text-align: left;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C['texte']};
                    border: none; border-radius: 8px;
                    padding: 9px 12px; font-size: 13px; text-align: left;
                }}
                QPushButton:hover {{ background: {C['card']}; }}
            """)

    def activer(self, actif: bool):
        self._actif = actif
        self._rendu()

    def set_compteur(self, n: int):
        self._compteur = n
        self._rendu()


# ══════════════════════════════════════════════════════════════
#  LIGNE SOURCE
# ══════════════════════════════════════════════════════════════
class LigneSource(QWidget):
    def __init__(self, nom: str, couleur: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(8)
        pt = QLabel('●')
        pt.setStyleSheet(f'color: {couleur}; font-size: 10px;')
        lay.addWidget(pt)
        lbl = QLabel(nom)
        lbl.setStyleSheet(f'color: {C["texte"]}; font-size: 11px;')
        lay.addWidget(lbl)
        lay.addStretch()
        self.statut = QLabel('⏳')
        self.statut.setStyleSheet(f'color: {C["jaune"]}; font-size: 10px;')
        lay.addWidget(self.statut)

    def maj_statut(self, ok: bool, compte: int):
        if ok:
            self.statut.setText(f'✓ {compte}')
            self.statut.setStyleSheet(f'color: {C["vert"]}; font-size: 10px;')
        else:
            self.statut.setText('✗')
            self.statut.setStyleSheet(f'color: {C["rouge"]}; font-size: 10px;')


# ══════════════════════════════════════════════════════════════
#  BOITE STATISTIQUE
# ══════════════════════════════════════════════════════════════
class BoiteStatistique(QFrame):
    def __init__(self, etiquette: str, couleur: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px; }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10); lay.setSpacing(2)
        self.val = QLabel('0')
        self.val.setStyleSheet(f'color: {couleur}; font-size: 22px; font-weight: 700;')
        lay.addWidget(self.val)
        etiq = QLabel(etiquette)
        etiq.setStyleSheet(f'color: {C["discret"]}; font-size: 10px;')
        lay.addWidget(etiq)

    def set_valeur(self, v):
        self.val.setText(str(v))


# ══════════════════════════════════════════════════════════════
#  PANNEAU GAUCHE
# ══════════════════════════════════════════════════════════════
class PanneauGauche(QWidget):
    filtre_change     = pyqtSignal(str)
    intervalle_change = pyqtSignal(int)
    telegram_clique   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('gauche')
        self.setFixedWidth(252)
        self.setStyleSheet(f'QWidget#gauche {{ background: {C["surface"]}; border-right: 1px solid {C["border"]}; }}')
        self._boutons_filtre: Dict[str, BoutonFiltre] = {}
        self._lignes_source: Dict[str, LigneSource] = {}
        self._construire()

    def _en_tete(self, texte: str) -> QLabel:
        l = QLabel(texte)
        l.setStyleSheet(f'color: {C["discret"]}; font-size: 10px; font-weight: 700; letter-spacing: 1px;')
        return l

    def _separateur(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f'color: {C["border"]};')
        return sep

    def _construire(self):
        # Scroll pour le contenu de la sidebar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }')

        contenu = QWidget()
        contenu.setStyleSheet('background: transparent;')
        lay = QVBoxLayout(contenu)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(0)

        # Titre app
        titre_lay = QHBoxLayout()
        ic = QLabel('⚡'); ic.setStyleSheet('font-size: 18px;')
        titre_lay.addWidget(ic)
        t = QLabel('MidEast Scanner')
        t.setStyleSheet(f'color: {C["texte"]}; font-size: 13px; font-weight: 700; margin-left: 4px;')
        titre_lay.addWidget(t)
        titre_lay.addStretch()
        lay.addLayout(titre_lay)
        lay.addSpacing(16)

        # ── SECTION : Filtres ─────────────────────────────────
        lay.addWidget(self._en_tete('FILTRES'))
        lay.addSpacing(6)

        for fid, icone, etiquette in FILTRES:
            btn = BoutonFiltre(fid, icone, etiquette)
            btn.clicked.connect(lambda checked, f=fid: self.filtre_change.emit(f))
            self._boutons_filtre[fid] = btn
            lay.addWidget(btn)
            if fid == 'aeroport':
                lay.addSpacing(2)
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet(f'background: {C["cyan"]}22; max-height: 1px;')
                lay.addWidget(sep)
                lay.addSpacing(2)
            if fid == 'tout':
                btn.activer(True)

        lay.addSpacing(18)

        # ── SECTION : Intervalle de scan ──────────────────────
        lay.addWidget(self._en_tete('INTERVALLE DE SCAN'))
        lay.addSpacing(8)

        grille = QHBoxLayout()
        grille.setSpacing(6)
        self._btns_intervalle: Dict[str, QPushButton] = {}
        for etiq, secs in INTERVALLES.items():
            btn = QPushButton(etiq)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, s=secs, e=etiq: self._choisir_intervalle(s, e))
            self._btns_intervalle[etiq] = btn
            grille.addWidget(btn)
        lay.addLayout(grille)
        self._styliser_intervalles('3 min')
        lay.addSpacing(18)

        # ── SECTION : Options ─────────────────────────────────
        lay.addWidget(self._en_tete('OPTIONS'))
        lay.addSpacing(6)

        self.cb_son   = QCheckBox('  🔔  Son sur alerte critique')
        self.cb_son.setChecked(True)
        lay.addWidget(self.cb_son)
        lay.addSpacing(4)

        self.cb_notif = QCheckBox('  📲  Notifications macOS')
        self.cb_notif.setChecked(True)
        lay.addWidget(self.cb_notif)
        lay.addSpacing(12)

        # Bouton Telegram
        self.btn_wa = QPushButton('📱  Telegram  ●')
        self.btn_wa.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wa.clicked.connect(self.telegram_clique)
        self._styliser_btn_telegram(False)
        lay.addWidget(self.btn_wa)
        lay.addSpacing(18)

        # ── SECTION : Sources ─────────────────────────────────
        lay.addWidget(self._en_tete('SOURCES RSS'))
        lay.addSpacing(6)

        for src in SOURCES:
            row = LigneSource(src['nom'], src['couleur'])
            self._lignes_source[src['nom']] = row
            lay.addWidget(row)

        lay.addStretch()
        ver = QLabel('v2.1 • Scan automatique actif')
        ver.setStyleSheet(f'color: {C["discret"]}; font-size: 10px;')
        lay.addWidget(ver)

        scroll.setWidget(contenu)
        racine_lay = QVBoxLayout(self)
        racine_lay.setContentsMargins(0, 0, 0, 0)
        racine_lay.addWidget(scroll)

    def _styliser_btn_telegram(self, actif: bool):
        if actif:
            self.btn_wa.setText('📲  Telegram  ✓ Actif')
            self.btn_wa.setStyleSheet(f"""
                QPushButton {{ background: #25d36622; color: #25d366;
                    border: 1px solid #25d36655; border-radius: 8px;
                    padding: 8px 12px; font-size: 12px; font-weight: 600; }}
                QPushButton:hover {{ background: #25d36635; }}
            """)
        else:
            self.btn_wa.setText('📲  Telegram  ○ Configurer')
            self.btn_wa.setStyleSheet(f"""
                QPushButton {{ background: {C['card']}; color: {C['discret']};
                    border: 1px solid {C['border']}; border-radius: 8px;
                    padding: 8px 12px; font-size: 12px; }}
                QPushButton:hover {{ color: #25d366; border-color: #25d36644; }}
            """)

    def _choisir_intervalle(self, secs: int, etiq: str):
        self._styliser_intervalles(etiq)
        self.intervalle_change.emit(secs)

    def _styliser_intervalles(self, actif: str):
        for etiq, btn in self._btns_intervalle.items():
            if etiq == actif:
                btn.setStyleSheet(f"""
                    QPushButton {{ background: {C['accent']}22; color: {C['accent']};
                        border: 1px solid {C['accent']}55; border-radius: 7px;
                        font-size: 12px; font-weight: 700; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{ background: {C['card']}; color: {C['discret']};
                        border: 1px solid {C['border']}; border-radius: 7px; font-size: 12px; }}
                    QPushButton:hover {{ color: {C['texte']}; }}
                """)

    def activer_filtre(self, fid: str):
        for f, btn in self._boutons_filtre.items():
            btn.activer(f == fid)

    def maj_compteurs(self, compteurs: dict):
        for fid, n in compteurs.items():
            if fid in self._boutons_filtre:
                self._boutons_filtre[fid].set_compteur(n)

    def maj_source(self, nom: str, ok: bool, compte: int):
        if nom in self._lignes_source:
            self._lignes_source[nom].maj_statut(ok, compte)

    def maj_statut_telegram(self, cfg):
        # Accepte bool (rétrocompat) ou dict
        if isinstance(cfg, bool):
            actif = cfg
        else:
            actif = cfg.get('wa_actif', False) or cfg.get('tg_actif', False)
        self._styliser_btn_telegram(actif)

    def son_actif(self) -> bool:
        return self.cb_son.isChecked()

    def notifs_actives(self) -> bool:
        return self.cb_notif.isChecked()


# ══════════════════════════════════════════════════════════════
#  PANNEAU CENTRAL
# ══════════════════════════════════════════════════════════════
class PanneauCentral(QWidget):
    recherche_changee = pyqtSignal(str)
    actualiser_clique = pyqtSignal()
    exporter_clique   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('centre')
        self._cartes: List[QWidget] = []
        self._construire()

    def _construire(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Barre supérieure
        barre = QWidget()
        barre.setStyleSheet(f'background: {C["surface"]}; border-bottom: 1px solid {C["border"]};')
        bl = QHBoxLayout(barre)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(10)

        self.champ_recherche = QLineEdit()
        self.champ_recherche.setPlaceholderText('🔍  Rechercher : aéroport, Iran, missile, Dubai…')
        self.champ_recherche.textChanged.connect(self.recherche_changee)
        bl.addWidget(self.champ_recherche)

        self.btn_actualiser = QPushButton('↻  Actualiser')
        self.btn_actualiser.setStyleSheet(f"""
            QPushButton {{ background: {C['accent']}18; color: {C['accent']};
                border: 1px solid {C['accent']}44; border-radius: 8px;
                padding: 8px 16px; font-size: 12px; font-weight: 600; }}
            QPushButton:hover {{ background: {C['accent']}30; }}
        """)
        self.btn_actualiser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_actualiser.clicked.connect(self.actualiser_clique)
        bl.addWidget(self.btn_actualiser)

        btn_csv = QPushButton('📥  CSV')
        btn_csv.setStyleSheet(f"""
            QPushButton {{ background: {C['card']}; color: {C['discret']};
                border: 1px solid {C['border']}; border-radius: 8px;
                padding: 8px 12px; font-size: 12px; }}
            QPushButton:hover {{ color: {C['texte']}; }}
        """)
        btn_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_csv.clicked.connect(self.exporter_clique)
        bl.addWidget(btn_csv)
        lay.addWidget(barre)

        # Zone de défilement
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(f'QScrollArea {{ background: {C["bg"]}; }}')

        self.conteneur = QWidget()
        self.conteneur.setStyleSheet(f'background: {C["bg"]};')
        self.flux_lay = QVBoxLayout(self.conteneur)
        self.flux_lay.setContentsMargins(16, 16, 16, 16)
        self.flux_lay.setSpacing(8)
        self.flux_lay.addStretch()
        self.scroll.setWidget(self.conteneur)
        lay.addWidget(self.scroll)

    def afficher_chargement(self):
        self._vider_cartes()
        msg = QLabel('⏳  Connexion aux sources en cours…')
        msg.setStyleSheet(f'color: {C["discret"]}; font-size: 14px;')
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flux_lay.insertWidget(0, msg)

    def afficher_vide(self, texte='Aucun résultat pour ce filtre.'):
        self._vider_cartes()
        msg = QLabel(f'🔭  {texte}')
        msg.setStyleSheet(f'color: {C["discret"]}; font-size: 14px;')
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flux_lay.insertWidget(0, msg)

    def afficher_articles(self, articles: List[Article], titre_section: str = ''):
        self._vider_cartes()
        if not articles:
            self.afficher_vide()
            return

        # Bannière de section aviation si présente en tête
        aviation = [a for a in articles if 'aeroport' in a.tags]
        autres   = [a for a in articles if 'aeroport' not in a.tags]

        if aviation:
            self._ajouter_separateur_section('✈️  AÉROPORTS & AVIATION', C['cyan'])
            for a in aviation[:30]:
                carte = CarteArticle(a)
                self._cartes.append(carte)
                self.flux_lay.insertWidget(self.flux_lay.count() - 1, carte)

        if autres:
            if aviation:
                self._ajouter_separateur_section('🌍  AUTRES ACTUALITÉS', C['discret'])
            for a in autres[:60]:
                carte = CarteArticle(a)
                self._cartes.append(carte)
                self.flux_lay.insertWidget(self.flux_lay.count() - 1, carte)

        self.scroll.verticalScrollBar().setValue(0)

    def _ajouter_separateur_section(self, texte: str, couleur: str):
        sep_w = QWidget()
        sep_w.setStyleSheet(f'background: transparent;')
        sep_lay = QHBoxLayout(sep_w)
        sep_lay.setContentsMargins(0, 8, 0, 4)

        ligne = QFrame()
        ligne.setFrameShape(QFrame.Shape.HLine)
        ligne.setStyleSheet(f'color: {couleur}44;')
        ligne.setFixedHeight(1)

        lbl = QLabel(texte)
        lbl.setStyleSheet(f"""
            QLabel {{ color: {couleur}; font-size: 11px; font-weight: 700;
                      letter-spacing: 1px; background: {C['bg']};
                      padding: 0 8px; }}
        """)

        sep_lay.addWidget(ligne, 1)
        sep_lay.addWidget(lbl)

        ligne2 = QFrame()
        ligne2.setFrameShape(QFrame.Shape.HLine)
        ligne2.setStyleSheet(f'color: {couleur}44;')
        ligne2.setFixedHeight(1)
        sep_lay.addWidget(ligne2, 3)

        self._cartes.append(sep_w)
        self.flux_lay.insertWidget(self.flux_lay.count() - 1, sep_w)

    def _vider_cartes(self):
        for c in self._cartes:
            self.flux_lay.removeWidget(c)
            c.deleteLater()
        self._cartes.clear()
        for i in reversed(range(self.flux_lay.count())):
            item = self.flux_lay.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if not isinstance(w, CarteArticle):
                    self.flux_lay.removeWidget(w)
                    w.deleteLater()

    def btn_chargement(self, en_cours: bool):
        if en_cours:
            self.btn_actualiser.setText('⏳  Scan en cours…')
            self.btn_actualiser.setEnabled(False)
        else:
            self.btn_actualiser.setText('↻  Actualiser')
            self.btn_actualiser.setEnabled(True)


# ══════════════════════════════════════════════════════════════
#  PANNEAU DROIT
# ══════════════════════════════════════════════════════════════
class PanneauDroit(QWidget):
    motcle_clique = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('droite')
        self.setFixedWidth(268)
        self.setStyleSheet(f'QWidget#droite {{ background: {C["surface"]}; border-left: 1px solid {C["border"]}; }}')
        self._btns_mc: List[QPushButton] = []
        self._construire()

    def _en_tete(self, texte: str) -> QLabel:
        l = QLabel(texte)
        l.setStyleSheet(f'color: {C["discret"]}; font-size: 10px; font-weight: 700; letter-spacing: 1px;')
        return l

    def _construire(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 16, 14, 16); lay.setSpacing(0)

        # Stats
        lay.addWidget(self._en_tete('STATISTIQUES'))
        lay.addSpacing(8)
        grille = QWidget()
        gl = QHBoxLayout(grille); gl.setSpacing(8); gl.setContentsMargins(0,0,0,0)
        col_g = QVBoxLayout(); col_g.setSpacing(8)
        col_d = QVBoxLayout(); col_d.setSpacing(8)

        self.stat_aviation = BoiteStatistique('Aviation', C['cyan'])
        self.stat_critique = BoiteStatistique('Critiques', C['rouge'])
        self.stat_total    = BoiteStatistique('Total', C['bleu'])
        self.stat_sources  = BoiteStatistique('Sources OK', C['vert'])

        col_g.addWidget(self.stat_aviation)
        col_g.addWidget(self.stat_critique)
        col_d.addWidget(self.stat_total)
        col_d.addWidget(self.stat_sources)
        gl.addLayout(col_g); gl.addLayout(col_d)
        lay.addWidget(grille)
        lay.addSpacing(14)

        # Notifications statut
        self.lbl_wa_statut = QLabel('💬  Notifications : non configurées')
        self.lbl_wa_statut.setStyleSheet(f'color: {C["discret"]}; font-size: 11px;')
        lay.addWidget(self.lbl_wa_statut)

        self.lbl_maj = QLabel('Dernière MAJ : —')
        self.lbl_maj.setStyleSheet(f'color: {C["discret"]}; font-size: 11px;')
        lay.addWidget(self.lbl_maj)
        lay.addSpacing(18)

        # Mots-clés
        lay.addWidget(self._en_tete('MOTS-CLÉS ACTIFS'))
        lay.addSpacing(8)

        mc_scroll = QScrollArea()
        mc_scroll.setWidgetResizable(True)
        mc_scroll.setFixedHeight(120)
        mc_scroll.setStyleSheet('QScrollArea { background: transparent; border: none; }')
        mc_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.conteneur_mc = QWidget()
        self.conteneur_mc.setStyleSheet('background: transparent;')
        self.mc_lay_outer = QVBoxLayout(self.conteneur_mc)
        self.mc_lay_outer.setContentsMargins(0,0,0,0); self.mc_lay_outer.setSpacing(5)
        mc_scroll.setWidget(self.conteneur_mc)
        lay.addWidget(mc_scroll)
        lay.addSpacing(18)

        # Timeline
        lay.addWidget(self._en_tete('ÉVÉNEMENTS RÉCENTS'))
        lay.addSpacing(8)

        tl_scroll = QScrollArea()
        tl_scroll.setWidgetResizable(True)
        tl_scroll.setStyleSheet('QScrollArea { background: transparent; border: none; }')
        tl_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.tl_conteneur = QWidget()
        self.tl_conteneur.setStyleSheet('background: transparent;')
        self.tl_lay = QVBoxLayout(self.tl_conteneur)
        self.tl_lay.setContentsMargins(0,0,0,0); self.tl_lay.setSpacing(0)
        self.tl_lay.addStretch()
        tl_scroll.setWidget(self.tl_conteneur)
        lay.addWidget(tl_scroll, 1)

    def maj_stats(self, total: int, aviation: int, critiques: int, sources_ok: int):
        self.stat_aviation.set_valeur(aviation)
        self.stat_critique.set_valeur(critiques)
        self.stat_total.set_valeur(total)
        self.stat_sources.set_valeur(sources_ok)
        self.lbl_maj.setText(f'Dernière MAJ : {datetime.now().strftime("%H:%M:%S")}')

    def maj_statut_telegram(self, cfg: dict):
        parties = []
        if cfg.get('wa_actif') and cfg.get('wa_phone'):
            tel = cfg['wa_phone'][-4:]
            parties.append(f'💬 WA …{tel}')
        if cfg.get('tg_actif') and cfg.get('tg_chat_id'):
            cid = cfg['tg_chat_id'][-4:]
            parties.append(f'📱 TG …{cid}')
        if parties:
            self.lbl_wa_statut.setText('  ✓  ' + '   '.join(parties))
            self.lbl_wa_statut.setStyleSheet('color: #25d366; font-size: 11px;')
        else:
            self.lbl_wa_statut.setText('💬  Notifications : non configurées')
            self.lbl_wa_statut.setStyleSheet(f'color: {C["discret"]}; font-size: 11px;')

    def maj_motscles(self, compteurs: dict):
        for btn in self._btns_mc:
            btn.deleteLater()
        self._btns_mc.clear()

        # Vider le layout
        for i in reversed(range(self.mc_lay_outer.count())):
            item = self.mc_lay_outer.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        tries = sorted(compteurs.items(), key=lambda x: -x[1])[:18]
        rangee_w = None
        rangee_lay = None
        for idx, (mc, n) in enumerate(tries):
            if n == 0:
                continue
            if idx % 3 == 0:
                rangee_w = QWidget(); rangee_w.setStyleSheet('background: transparent;')
                rangee_lay = QHBoxLayout(rangee_w)
                rangee_lay.setContentsMargins(0,0,0,0); rangee_lay.setSpacing(5)
                self.mc_lay_outer.addWidget(rangee_w)
            btn = QPushButton(f'{mc}  {n}')
            btn.setStyleSheet(f"""
                QPushButton {{ background: {C['card']}; color: {C['discret']};
                    border: 1px solid {C['border']}; border-radius: 12px;
                    padding: 3px 9px; font-size: 10px; }}
                QPushButton:hover {{ border-color: {C['accent']}; color: {C['accent']}; }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=mc: self.motcle_clique.emit(k))
            self._btns_mc.append(btn)
            if rangee_lay:
                rangee_lay.addWidget(btn)

    def maj_timeline(self, articles: List[Article]):
        for i in reversed(range(self.tl_lay.count())):
            item = self.tl_lay.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        importants = [a for a in articles if a.niveau >= 1][:15]
        if not importants:
            msg = QLabel('Aucun événement récent.')
            msg.setStyleSheet(f'color: {C["discret"]}; font-size: 11px;')
            self.tl_lay.insertWidget(0, msg)
            return

        for a in importants:
            rangee = QWidget(); rangee.setStyleSheet('background: transparent;')
            rl = QHBoxLayout(rangee)
            rl.setContentsMargins(0, 5, 0, 5); rl.setSpacing(8)
            icone_niv = NIVEAUX[a.niveau][0]
            h = QLabel(a.date.strftime('%H:%M'))
            h.setStyleSheet(f'color: {C["discret"]}; font-size: 10px;')
            h.setFixedWidth(34)
            rl.addWidget(h)
            ic = QLabel(icone_niv); ic.setStyleSheet('font-size: 10px;')
            rl.addWidget(ic)
            tl = QLabel(a.titre[:55] + ('…' if len(a.titre) > 55 else ''))
            tl.setStyleSheet(f'color: {C["texte"]}; font-size: 11px;')
            tl.setWordWrap(True)
            rl.addWidget(tl, 1)
            self.tl_lay.insertWidget(self.tl_lay.count() - 1, rangee)
            sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet(f'color: {C["border"]};')
            self.tl_lay.insertWidget(self.tl_lay.count() - 1, sep)


# ══════════════════════════════════════════════════════════════
#  FENÊTRE PRINCIPALE
# ══════════════════════════════════════════════════════════════
class FenetrePrincipale(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('⚡ MidEast Intel Scanner')
        self.resize(1340, 820)
        self.setMinimumSize(980, 640)

        self._tous_articles: List[Article] = []
        self._filtre_actif   = 'tout'
        self._recherche      = ''
        self._sources_ok     = 0
        self._non_lus        = 0
        self._countdown      = INTERVALLE_PAR_DEFAUT
        self._intervalle     = INTERVALLE_PAR_DEFAUT
        self._worker: Optional[WorkerRecup] = None
        self._cfg_telegram   = _charger_config()
        self._tg_envoyes     = set()   # IDs déjà envoyés par Telegram

        self._construire_ui()
        self._construire_barre_statut()
        self._connecter_signaux()
        self._demarrer_minuterie()

        # Appliquer config Telegram au démarrage
        self.panneau_gauche.maj_statut_telegram(self._cfg_telegram.get('actif', False))
        self.panneau_droit.maj_statut_telegram(self._cfg_telegram)

        self.panneau_central.afficher_chargement()
        self._lancer_scan()

    def _construire_ui(self):
        racine = QWidget(); racine.setObjectName('root')
        self.setCentralWidget(racine)
        lay = QHBoxLayout(racine)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(0)
        self.panneau_gauche  = PanneauGauche()
        self.panneau_central = PanneauCentral()
        self.panneau_droit   = PanneauDroit()
        lay.addWidget(self.panneau_gauche)
        lay.addWidget(self.panneau_central, 1)
        lay.addWidget(self.panneau_droit)

    def _construire_barre_statut(self):
        sb = self.statusBar()
        sb.setStyleSheet(f"""
            QStatusBar {{ background: {C['surface']}; color: {C['discret']};
                border-top: 1px solid {C['border']}; font-size: 11px; padding: 2px 8px; }}
        """)
        self.sb_articles  = QLabel('Chargement…')
        self.sb_heure     = QLabel('')
        self.sb_countdown = QLabel(f'Prochain scan : {self._intervalle}s')
        sb.addWidget(self.sb_articles)
        sb.addPermanentWidget(self.sb_heure)
        sb.addPermanentWidget(self.sb_countdown)

    def _connecter_signaux(self):
        self.panneau_gauche.filtre_change.connect(self._sur_filtre)
        self.panneau_gauche.intervalle_change.connect(self._sur_intervalle)
        self.panneau_gauche.telegram_clique.connect(self._ouvrir_config_telegram)
        self.panneau_central.recherche_changee.connect(self._sur_recherche)
        self.panneau_central.actualiser_clique.connect(self._lancer_scan)
        self.panneau_central.exporter_clique.connect(self._exporter_csv)
        self.panneau_droit.motcle_clique.connect(self._sur_motcle)

    def _demarrer_minuterie(self):
        self._minuterie = QTimer(self)
        self._minuterie.timeout.connect(self._tic)
        self._minuterie.start(1000)

    def _tic(self):
        self._countdown -= 1
        self.sb_countdown.setText(f'Prochain scan : {max(0, self._countdown)}s')
        if self._countdown <= 0:
            self._lancer_scan()

    def _sur_intervalle(self, secs: int):
        self._intervalle = secs
        self._countdown  = secs

    # ── Scan ─────────────────────────────────────────────────
    def _lancer_scan(self):
        if self._worker and self._worker.isRunning():
            return
        self._countdown  = self._intervalle
        self._sources_ok = 0
        self.panneau_central.btn_chargement(True)
        self._worker = WorkerRecup()
        self._worker.articles_prets.connect(self._sur_articles)
        self._worker.statut_source.connect(self._sur_statut_source)
        self._worker.start()

    def _sur_statut_source(self, nom: str, ok: bool, compte: int):
        self.panneau_gauche.maj_source(nom, ok, compte)
        if ok:
            self._sources_ok += 1

    def _sur_articles(self, nouveaux: List[Article]):
        connus = {a.id for a in self._tous_articles}
        frais  = [a for a in nouveaux if a.id not in connus]
        # Tri : aviation en tête, puis par date
        self._tous_articles = sorted(
            frais + self._tous_articles,
            key=lambda a: (-a.priorite, -a.date.timestamp()),
        )[:300]

        self._non_lus += len(frais)
        self._maj_affichage()
        self.panneau_central.btn_chargement(False)
        self.sb_heure.setText(f'Dernière MAJ : {datetime.now().strftime("%H:%M:%S")}')

        # Notifications & Telegram
        seuil = self._cfg_telegram.get('seuil_niveau', 2)
        for a in frais:
            if a.niveau >= 2:
                self._notifier_mac(a)
            if a.niveau >= 1 and self.panneau_gauche.son_actif():
                self._jouer_son()
                break
        self._traiter_telegram(frais, seuil)

    # ── Affichage ────────────────────────────────────────────
    def _maj_affichage(self):
        articles = self._filtres()
        compteurs = self._calculer_compteurs()
        compteurs_mc = {mc: sum(1 for a in self._tous_articles if mc in a.texte)
                        for mc in MOTS_CLES_TOP}
        self.panneau_gauche.maj_compteurs(compteurs)
        self.panneau_central.afficher_articles(articles)
        self.panneau_droit.maj_stats(
            len(self._tous_articles),
            sum(1 for a in self._tous_articles if 'aeroport' in a.tags),
            sum(1 for a in self._tous_articles if a.niveau == 2),
            self._sources_ok,
        )
        self.panneau_droit.maj_motscles(compteurs_mc)
        self.panneau_droit.maj_timeline(self._tous_articles)
        self.sb_articles.setText(
            f'{len(articles)} articles  •  '
            f'{sum(1 for a in articles if "aeroport" in a.tags)} aviation  •  '
            f'{self._non_lus} nouveaux'
        )

    def _filtres(self) -> List[Article]:
        q = self._recherche.lower().strip()
        f = self._filtre_actif
        result = [
            a for a in self._tous_articles
            if (f == 'tout' or (f == 'breaking' and a.breaking) or f in a.tags)
            and (not q or q in a.texte)
        ]
        # Garder tri : aviation en tête
        return sorted(result, key=lambda a: (-a.priorite, -a.date.timestamp()))

    def _calculer_compteurs(self) -> dict:
        c = {
            'tout':     len(self._tous_articles),
            'breaking': sum(1 for a in self._tous_articles if a.breaking),
            'aeroport': sum(1 for a in self._tous_articles if 'aeroport' in a.tags),
        }
        for fid, _, _ in FILTRES:
            if fid not in c:
                c[fid] = sum(1 for a in self._tous_articles if fid in a.tags)
        return c

    def _sur_filtre(self, fid: str):
        self._filtre_actif = fid
        self._non_lus = 0
        self.panneau_gauche.activer_filtre(fid)
        self._maj_affichage()

    def _sur_recherche(self, texte: str):
        self._recherche = texte
        self._maj_affichage()

    def _sur_motcle(self, mc: str):
        self.panneau_central.champ_recherche.setText(mc)
        self._recherche = mc
        self._maj_affichage()

    # ── Notifications (WhatsApp + Telegram) ──────────────────
    def _ouvrir_config_telegram(self):
        dlg = DialogTelegram(self._cfg_telegram, self)
        dlg.config_sauvegardee.connect(self._sur_config_telegram)
        dlg.exec()

    def _sur_config_telegram(self, cfg: dict):
        self._cfg_telegram = cfg
        self.panneau_gauche.maj_statut_telegram(cfg)
        self.panneau_droit.maj_statut_telegram(cfg)

    def _traiter_telegram(self, frais: List[Article], seuil: int):
        a_envoyer = [
            a for a in frais
            if a.niveau >= seuil and a.id not in self._tg_envoyes
        ][:3]  # max 3 par scan

        for article in a_envoyer:
            self._tg_envoyes.add(article.id)
            msg = _formater_message_alerte(article)

            # WhatsApp CallMeBot
            if self._cfg_telegram.get('wa_actif'):
                phone  = self._cfg_telegram.get('wa_phone', '')
                apikey = self._cfg_telegram.get('wa_apikey', '')
                if phone and apikey:
                    def _envoi_wa(p=phone, k=apikey, m=msg):
                        _envoyer_whatsapp(p, k, m)
                    threading.Thread(target=_envoi_wa, daemon=True).start()

            # Telegram Bot
            if self._cfg_telegram.get('tg_actif'):
                token   = self._cfg_telegram.get('tg_token', '')
                chat_id = self._cfg_telegram.get('tg_chat_id', '')
                if token and chat_id:
                    def _envoi_tg(ci=chat_id, tk=token, m=msg):
                        _envoyer_telegram(ci, tk, m)
                    threading.Thread(target=_envoi_tg, daemon=True).start()

    # ── Notification macOS ────────────────────────────────────
    def _notifier_mac(self, a: Article):
        if not self.panneau_gauche.notifs_actives():
            return
        try:
            titre  = a.titre.replace('"', "'")[:100]
            source = a.source.replace('"', "'")
            icone  = '✈️' if 'aeroport' in a.tags else NIVEAUX[a.niveau][0]
            script = (
                f'display notification "{titre}" '
                f'with title "{icone} MidEast Scanner — {source}" '
                f'sound name "Sosumi"'
            )
            subprocess.Popen(['osascript', '-e', script],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _jouer_son(self):
        try:
            subprocess.Popen(['afplay', '/System/Library/Sounds/Sosumi.aiff'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    # ── Export CSV ────────────────────────────────────────────
    def _exporter_csv(self):
        articles = self._filtres()
        if not articles:
            QMessageBox.information(self, 'Export CSV', 'Aucun article à exporter.')
            return
        chemin, _ = QFileDialog.getSaveFileName(
            self, 'Exporter les articles',
            f'mideast_scan_{datetime.now():%Y%m%d_%H%M}.csv', 'CSV (*.csv)')
        if not chemin:
            return
        try:
            with open(chemin, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['Date', 'Source', 'Niveau', 'Aviation', 'Tags', 'Titre', 'Lien'])
                for a in articles:
                    w.writerow([
                        a.date.strftime('%Y-%m-%d %H:%M'), a.source,
                        NIVEAUX[a.niveau][2],
                        '✈️' if 'aeroport' in a.tags else '',
                        ','.join(a.tags), a.titre, a.lien,
                    ])
            QMessageBox.information(self, 'Export CSV', f'✓ {len(articles)} articles exportés.')
        except Exception as e:
            QMessageBox.warning(self, 'Erreur', str(e))


# ══════════════════════════════════════════════════════════════
#  ICÔNE BARRE DE MENU
# ══════════════════════════════════════════════════════════════
def _creer_icone(critique: bool = False) -> QIcon:
    px = QPixmap(22, 22)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    col = QColor(C['rouge'] if critique else C['accent'])
    p.setBrush(QBrush(col)); p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(3, 3, 16, 16)
    p.setPen(QPen(QColor(C['texte']), 1.5))
    for i in range(4):
        a = math.radians(i * 45)
        p.drawLine(11, 11, int(11 + 5*math.cos(a)), int(11 + 5*math.sin(a)))
    p.end()
    return QIcon(px)


class IconeMenuBar(QSystemTrayIcon):
    def __init__(self, fenetre: FenetrePrincipale, parent=None):
        super().__init__(parent)
        self._fenetre = fenetre
        self.setIcon(_creer_icone(False))
        self.setToolTip('MidEast Intel Scanner')
        self._menu = QMenu()
        self._actions_news: List[QAction] = []
        self._construire_menu()
        self.setContextMenu(self._menu)
        self.activated.connect(self._sur_activation)

    def _construire_menu(self):
        self._menu.clear()
        titre = QAction('⚡  MidEast Intel Scanner', self._menu)
        titre.setEnabled(False)
        self._menu.addAction(titre)
        self._menu.addSeparator()

        self._actions_news = []
        for _ in range(6):
            a = QAction('', self._menu)
            a.setVisible(False)
            self._menu.addAction(a)
            self._actions_news.append(a)

        self._menu.addSeparator()
        ouvrir = QAction('🖥  Ouvrir le scanner', self._menu)
        ouvrir.triggered.connect(self._ouvrir)
        self._menu.addAction(ouvrir)
        actu = QAction('↻  Actualiser', self._menu)
        actu.triggered.connect(self._fenetre._lancer_scan)
        self._menu.addAction(actu)
        wa = QAction('📱  Config Telegram…', self._menu)
        wa.triggered.connect(self._fenetre._ouvrir_config_telegram)
        self._menu.addAction(wa)
        self._menu.addSeparator()
        quitter = QAction('✕  Quitter', self._menu)
        quitter.triggered.connect(QApplication.quit)
        self._menu.addAction(quitter)

    def maj_articles(self, articles: List[Article]):
        critiques = [a for a in articles if a.niveau == 2]
        aviation  = [a for a in articles if 'aeroport' in a.tags]
        self.setIcon(_creer_icone(len(critiques) > 0))
        info_wa = '  📱✓' if self._fenetre._cfg_telegram.get('actif') else ''
        if critiques:
            self.setToolTip(f'⚡ Scanner — {len(critiques)} critique(s)  ✈️ {len(aviation)}{info_wa}')
        else:
            self.setToolTip(f'⚡ Scanner — {len(articles)} articles  ✈️ {len(aviation)}{info_wa}')

        # Priorité : aviation en tête, puis critiques
        top_aviation = aviation[:3]
        top_autres   = [a for a in critiques if 'aeroport' not in a.tags][:3]
        selection    = (top_aviation + top_autres)[:6]

        for i, action in enumerate(self._actions_news):
            if i < len(selection):
                a = selection[i]
                pfx = '✈️ ' if 'aeroport' in a.tags else NIVEAUX[a.niveau][0] + ' '
                action.setText((pfx + a.titre)[:65] + ('…' if len(a.titre) > 60 else ''))
                action.setVisible(True)
                try: action.triggered.disconnect()
                except: pass
                action.triggered.connect(lambda checked, url=a.lien: webbrowser.open(url))
            else:
                action.setVisible(False)

    def _ouvrir(self):
        self._fenetre.show(); self._fenetre.raise_(); self._fenetre.activateWindow()

    def _sur_activation(self, raison):
        if raison == QSystemTrayIcon.ActivationReason.Trigger:
            if self._fenetre.isVisible(): self._fenetre.hide()
            else: self._ouvrir()


# ══════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName('MidEast Intel Scanner')
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE_GLOBAL)

    fenetre = FenetrePrincipale()
    fenetre.show()

    icone = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        icone = IconeMenuBar(fenetre, app)
        icone.show()
        original = fenetre._sur_articles
        def _patched(nouveaux):
            original(nouveaux)
            if icone: icone.maj_articles(fenetre._tous_articles)
        fenetre._sur_articles = _patched
        if fenetre._worker:
            try: fenetre._worker.articles_prets.disconnect()
            except: pass
            fenetre._worker.articles_prets.connect(fenetre._sur_articles)

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
