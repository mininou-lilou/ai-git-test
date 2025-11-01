import os
import sys
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai

# --- Configuration ---
# Récupération des secrets via les variables d'environnement définies dans GitHub Actions
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")

# Le destinataire est le premier argument passé au script (l'email du committer)
if len(sys.argv) < 3:
    print("Erreur: L'email du destinataire et la liste des fichiers modifiés sont requis.")
    sys.exit(1)

RECIPIENT_EMAIL = sys.argv[1]
CHANGED_FILES = sys.argv[2].split()

# --- Fonctions d'aide ---

def get_file_content(file_path):
    """Lit le contenu d'un fichier."""
    try:
        # Lire les 100 premières lignes pour éviter de dépasser la limite de tokens
        with open(file_path, 'r', encoding='utf-8') as f:
            content = "".join(f.readlines()[:100])
        return f"--- Contenu du fichier: {file_path} ---\n{content}\n"
    except Exception as e:
        return f"--- Impossible de lire le fichier: {file_path} (Erreur: {e}) ---\n"

def run_typy_verification():
    """Exécute la vérification Typy et retourne le résultat."""
    print("Début de la vérification Typy...")
    try:
        # Exécuter 'typy verify'
        # Nous utilisons 'capture_output=True' pour récupérer stdout et stderr
        # 'text=True' pour décoder la sortie en texte
        result = subprocess.run(
            ['typy', 'verify'],
            capture_output=True,
            text=True,
            check=False # Ne lève pas d'exception en cas d'échec (code de retour non nul)
        )
        
        # Le code de retour est 0 si tout est OK, non nul en cas d'erreur de typage
        typy_success = result.returncode == 0
        
        # Combiner stdout et stderr pour le rapport complet
        typy_report = result.stdout + result.stderr
        
        print(f"Vérification Typy terminée. Succès: {typy_success}")
        
        return typy_success, typy_report
        
    except FileNotFoundError:
        # Cela ne devrait pas arriver si 'typy' est installé, mais c'est une bonne pratique
        return False, "Erreur: La commande 'typy' n'a pas été trouvée. Assurez-vous que Typy est installé."
    except Exception as e:
        return False, f"Erreur inattendue lors de l'exécution de Typy: {e}"

def generate_prompt(changed_files, typy_report):
    """Génère le prompt pour l'IA en incluant le contenu des fichiers et le rapport Typy."""
    
    typy_section = ""
    if typy_report:
        typy_section = (
            "--- Rapport de Vérification Typy ---\n"
            f"{typy_report}\n"
            "------------------------------------\n\n"
        )
        
    prompt = (
        "Vous êtes un expert en revue de code et en typage strict (Typy). Votre tâche est d'analyser les changements de code suivants, "
        "en vous concentrant sur la qualité, la cohérence, les erreurs potentielles et les améliorations. "
        "**Priorité absolue :** Si le 'Rapport de Vérification Typy' ci-dessous contient des erreurs, vous devez les mettre en évidence "
        "et expliquer clairement au développeur comment les corriger pour que le push soit accepté. "
        "Après l'analyse, vous devez générer une réponse **uniquement** sous forme de code HTML complet et esthétique "
        "pour un e-mail de feedback. L'e-mail doit être très beau, professionnel et convivial. "
        "Si le code est impeccable (y compris Typy), dites-le. S'il y a des erreurs ou des suggestions, mentionnez-les clairement, "
        "en indiquant les lignes si possible, et proposez des corrections. "
        "Le code HTML doit être complet (avec <html>, <body>, etc.) et utiliser des styles en ligne (CSS) "
        "pour garantir un bon affichage dans tous les clients de messagerie. Utilisez une palette de couleurs agréable (par exemple, bleu, vert, gris clair)."
        "\n\n"
        f"{typy_section}"
        "--- Fichiers Modifiés ---\n"
    )
    
    for file in changed_files:
        # Ne pas analyser les fichiers de configuration de GitHub Actions ou les fichiers binaires
        if file.startswith('.github/') or file.endswith(('.png', '.jpg', '.gif', '.bin')):
            continue
        prompt += get_file_content(file)
        
    return prompt

def get_ai_review(prompt):
    """Appelle l'API Gemini pour obtenir la revue de code HTML."""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Utilisation d'un modèle rapide et efficace
            contents=prompt
        )
        
        # L'IA est instruite de renvoyer uniquement le code HTML
        # On essaie d'extraire le bloc de code si l'IA l'a mis dans des balises markdown
        html_content = response.text.strip()
        if html_content.startswith("```html"):
            html_content = html_content.strip("```html").strip("```").strip()
            
        return html_content
        
    except Exception as e:
        return f"<h1>Erreur d'API Gemini</h1><p>Impossible d'obtenir la revue de code. Erreur: {e}</p>"

def send_email(recipient, subject, html_body):
    """Envoie l'email HTML via SMTP (Gmail)."""
    try:
        # Configuration de l'email
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Attacher le corps HTML
        msg.attach(MIMEText(html_body, 'html'))
        
        # Connexion au serveur SMTP de Gmail
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        
        # Envoi de l'email
        server.sendmail(SENDER_EMAIL, recipient, msg.as_string())
        server.close()
        
        print(f"Succès: Email de revue de code envoyé à {recipient}")
        
    except Exception as e:
        print(f"Erreur: Échec de l'envoi de l'email à {recipient}. Vérifiez le mot de passe d'application Gmail. Erreur: {e}")
        # En cas d'échec, nous affichons le corps HTML pour le débogage
        print("\n--- Contenu HTML non envoyé (pour débogage) ---\n")
        print(html_body)
        print("\n----------------------------------------------------\n")
        # Nous ne levons pas d'exception ici pour ne pas bloquer le workflow
        # si l'envoi d'email échoue après une revue réussie.

# --- Logique principale ---

print(f"Début de l'analyse pour le push de: {RECIPIENT_EMAIL}")
print(f"Fichiers modifiés: {', '.join(CHANGED_FILES)}")

# 1. Exécuter la vérification Typy
typy_success, typy_report = run_typy_verification()

# 2. Préparer le prompt pour l'IA (inclut le rapport Typy)
review_prompt = generate_prompt(CHANGED_FILES, typy_report)

# 3. Obtenir la revue de l'IA
# Le sujet de l'email dépendra du succès de Typy
if typy_success:
    email_subject = "✅ Revue de Code Automatisée - Succès Typy"
else:
    email_subject = "❌ Revue de Code Automatisée - Échec Typy"

html_review = get_ai_review(review_prompt)

# 4. Envoyer l'email
send_email(RECIPIENT_EMAIL, email_subject, html_review)

# 5. Déterminer le code de sortie
# Le script retourne le code de sortie de Typy.
# Si Typy échoue, le script échoue, ce qui bloquera le workflow GitHub Actions.
# C'est la méthode pour "bloquer le push" comme demandé.
if not typy_success:
    print("Échec de la vérification Typy. Le script va se terminer avec un code d'erreur pour bloquer le push.")
    # Le code de retour de Typy est déjà dans le rapport, mais nous allons utiliser 1 pour une erreur générique
    sys.exit(1)
else:
    print("Vérification Typy réussie. Le script va se terminer avec succès.")
    sys.exit(0)
