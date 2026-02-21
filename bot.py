import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8569474905:AAGnHq6JgyFq-M18KBk2gOypQwnUHH53IGk')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
TELEGRAM_URL = f'https://api.telegram.org/bot{BOT_TOKEN}'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}'

SYSTEM_PROMPT = """Tu es Liora, agent expert en pronostics hippiques PMU. Suis ces regles ABSOLUES:

A - PROTOCOLE REPRODUCTIBILITE
Temperature=0. Traitement TOUJOURS par N dossard croissant. Scoring mecanique chiffre par chiffre. Si deja repondu, reproduis exactement la meme reponse. Interdit: environ, approximativement, estime, probablement, semble.
REGLE ANTI-TRICHE: Si course passee, analyser UNIQUEMENT avec donnees AVANT la course. INTERDICTION consulter resultats/arrivee.

B - COLLECTE DONNEES (non affiche)
Min 5 sources: pmu.fr, geny.com, paris-turf.com, turf.bzh, boturfers.fr, pronostics-courses.fr, zeturf.fr
Pour chaque partant par N croissant: musique 5 der., perf. distance +-200m, perf. hippodrome, forme 90j, gains carriere, age, taux jockey 30j, affinites jockey-cheval, exp. trac, taux entraineur 60j, forme ecurie, specialisation, terrain. SANS consulter cotes pendant scoring. Donnee introuvable = score minimum.

C - BAREME SCORING
Cheval 40pts:
- Musique 5 der: 1-3e=8pts, 4-5e=5pts, hors top5=2pts, NP=0pt
- Perf distance +-200m: ratio (VP/courses) = 0-10pts
- Perf hippodrome: ratio (VP/courses) = 0-8pts
- Forme 90j: hausse=7pts, stable=4pts, baisse=1pt
- Gains carriere: top20% peloton=5pts, top50%=3pts, reste=1pt
- Age/Sexe: 4-7ans=2pts bonus
Jockey 25pts:
- Tx reussite 30j: >20%=10pts, >12%=7pts, >6%=4pts, reste=1pt
- Affinites J-C: ratio (VP/courses ensemble) = 0-8pts
- Exp hippodrome+trac: >3 vict=7pts, >1 vict=4pts, reste=1pt
Entraineur 20pts:
- Tx reussite 60j: >18%=8pts, >10%=5pts, >5%=3pts, reste=1pt
- Forme ecurie 30j: serie gagnante=7pts, normale=4pts, difficulte=1pt
- Specialite type/terrain: expert=5pts, experimente=3pts, debutant=1pt
Course 15pts:
- Terrain vs historique cheval: accord=8pts, acceptable=5pts, defavorable=0pt
- Type piste: preference confirmee=4pts, neutre=2pts
- Corde/Autostart: favorable selon historique=3pts, neutre=1pt

D - CALCUL
Score Total = somme points (max 100). Proba Trio = (Score / somme scores 8 premiers) x 100.
Departage egalite: 1) musique (somme 5 pos, NP=6, plus bas gagne) 2) gains (plus eleve) 3) N dossard (plus bas).

E - ANTI-BIAIS
INTERDICTION consulter cotes avant classement final. Si classement = favoris par cote = ERREUR recommencer. Outsider PEUT etre haut, favori PEUT etre bas.

F - FORMAT SORTIE OBLIGATOIRE (UNIQUEMENT CECI):
R?C? DATE - HIPPODROME | Distancem Terrain | Partants | Depart HHMM
1. N°X - NomCheval - XX/100 - XX% - Cote X.X - mot1 mot2 mot3
2. N°X - NomCheval - XX/100 - XX% - Cote X.X - mot1 mot2 mot3
[...jusqu'a 8 chevaux, TRIES SCORE DECROISSANT]
Sources: X/7
REGLE: Rang1 = score max. Si rang1 != score max = ERREUR recommencer tri.

G - COMMANDES
/quint ou 'quinte du jour' = analyse Quinte PMU du jour
/analyse R1C1 = course specifique (ex: R5C3, R1C8 15022026)
/resultats [date] = verifier resultats et rentabilite
/historique = bilan performances
/cheval NomCheval = fiche detaillee"""

def send_message(chat_id, text):
    try:
        resp = requests.post(
            f'{TELEGRAM_URL}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'},
            timeout=30
        )
        return resp.json()
    except Exception as e:
        print(f'Erreur envoi message: {e}')
        return None

def send_typing(chat_id):
    try:
        requests.post(
            f'{TELEGRAM_URL}/sendChatAction',
            json={'chat_id': chat_id, 'action': 'typing'},
            timeout=10
        )
    except:
        pass

def call_gemini(user_message):
    payload = {
        'contents': [
            {
                'role': 'user',
                'parts': [{'text': SYSTEM_PROMPT + '\n\n---\n\nDemande utilisateur: ' + user_message}]
            }
        ],
        'generationConfig': {
            'temperature': 0.0,
            'maxOutputTokens': 2000,
            'topP': 1.0,
            'topK': 1
        },
        'tools': [{'google_search': {}}]
    }
    resp = requests.post(GEMINI_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data['candidates'][0]['content']['parts'][0]['text']

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        if not data or 'message' not in data:
            return jsonify({'ok': True})
        
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        
        if not text:
            return jsonify({'ok': True})
        
        send_typing(chat_id)
        
        if text == '/start':
            reply = (
                'Bonjour ! Je suis Liora, ton agent PMU v6.\n\n'
                'Commandes disponibles:\n'
                '/quint - Analyse Quinte du jour\n'
                '/analyse R1C1 - Course specifique\n'
                '/resultats - Verifier resultats\n'
                '/historique - Bilan performances\n'
                '/cheval NomCheval - Fiche cheval\n\n'
                'Scoring 100pts | Anti-biais cotes | Sources x7'
            )
            send_message(chat_id, reply)
        elif text == '/aide' or text == '/help':
            reply = (
                'LIORA PMU v6 - Mode d emploi:\n\n'
                'Analyse Quinte: /quint\n'
                'Course specifique: /analyse R5C3\n'
                'Course + date: /analyse R1C8 20022026\n'
                'Resultats du jour: /resultats\n'
                'Resultats date: /resultats 20022026\n'
                'Historique: /historique 10\n'
                'Fiche cheval: /cheval JAZZ DE PADD\n\n'
                'Scoring: Cheval 40pts | Jockey 25pts | Entraineur 20pts | Course 15pts\n'
                'Sources: pmu.fr, geny.com, paris-turf, turf.bzh, boturfers, pronostics-courses, zeturf'
            )
            send_message(chat_id, reply)
        else:
            try:
                reply = call_gemini(text)
                send_message(chat_id, reply)
            except requests.exceptions.Timeout:
                send_message(chat_id, 'Analyse en cours, cela prend un peu de temps... Reessaie dans 30 secondes.')
            except Exception as e:
                send_message(chat_id, f'Erreur lors de l analyse: {str(e)[:200]}')
        
        return jsonify({'ok': True})
    
    except Exception as e:
        print(f'Erreur webhook: {e}')
        return jsonify({'ok': True})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'bot': 'Liora PMU v6'})

@app.route('/', methods=['GET'])
def index():
    return jsonify({'message': 'Liora PMU Bot actif', 'version': '6.0'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'Liora PMU Bot demarre sur port {port}')
    app.run(host='0.0.0.0', port=port, debug=False)
