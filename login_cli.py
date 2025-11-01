# login_cli.py
import typer
from typer import Typer, echo, style
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich import print as rprint
import getpass
import httpx
import json

app = Typer(help="Système de login interactif en CLI")

console = Console()

# Simuler une base de données d'utilisateurs
USERS_DB = {
    "admin": {"password": "secret123", "role": "admin"},
    "user": {"password": "user456", "role": "user"}
}

def fake_api_login(username: str, password: str) -> dict:
    """Simule une API de login"""
    if username in USERS_DB and USERS_DB[username]["password"] == password:
        return {"success": True, "token": "fake-jwt-token-123", "role": USERS_DB[username]["role"]}
    else:
        return {"success": False, "error": "Identifiants incorrects"}

@app.command()
def login():
    """Page de login interactive dans le terminal"""
    console.clear()
    console.rule("[bold blue] Système de Connexion [/bold blue]")

    # Affichage du panneau de login
    console.print(Panel(
        "[bold cyan]Bienvenue ![/bold cyan]\n\nEntrez vos identifiants pour vous connecter.",
        title="Login",
        style="bold white on #1a1a2e"
    ))

    # Saisie du nom d'utilisateur
    username = Prompt.ask(" [green]👤 Nom d'utilisateur[/green]")
    
    # Saisie du mot de passe (masqué)
    password = getpass.getpass(" [red]🔒 Mot de passe[/red]: ")

    console.print("\n[bold yellow]Connexion en cours...[/bold yellow]")

    # Simulation appel API
    result = fake_api_login(username, password)

    if result["success"]:
        rprint(Panel(
            f"[bold green]Connexion réussie ![/bold green]\n\n"
            f"👋 Bienvenue [bold]{username}[/bold] !\n"
            f"🔑 Token: [dim]{result['token']}[/dim]\n"
            f"🛡️ Rôle: [bold]{result['role']}[/bold]",
            title="Succès",
            style="bold green"
        ))
    else:
        rprint(Panel(
            f"[bold red]Échec de connexion[/bold red]\n\n"
            f"❌ {result['error']}",
            title="Erreur",
            style="bold red"
        ))

@app.command()
def register():
    """Inscription d'un nouvel utilisateur (simulé)"""
    console.clear()
    console.rule("[bold magenta] Inscription [/bold magenta]")

    username = Prompt.ask(" [green]👤 Choisir un nom d'utilisateur[/green]")
    if username in USERS_DB:
        rprint(Panel("[bold red]Ce nom existe déjà ![/bold red]", title="Erreur"))
        return

    password = getpass.getpass(" [red]🔒 Choisir un mot de passe[/red]: ")
    role = "user"  # par défaut

    USERS_DB[username] = {"password": password, "role": role}

    rprint(Panel(
        f"[bold green]Compte créé avec succès ![/bold green]\n\n"
        f"Utilisateur: [bold]{username}[/bold]\n"
        f"Rôle: {role}",
        title="Inscription réussie"
    ))

if __name__ == "__main__":
    app()