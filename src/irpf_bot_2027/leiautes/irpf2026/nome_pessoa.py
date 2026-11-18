"""
Regra do programa para nome de pessoa física cadastrada na declaração (dependente; também titular e
alimentando).

Origem: classe ValidadorNomeIRPF do IRPF 2026 (lida com javap), usada no nome do dependente. O nome é
dividido nas partes separadas por espaço; é erro (severidade 3):
    - mais de 60 caracteres ou mais de 15 partes;
    - parte com número ("Nome não pode ter números.") ou com caractere que não seja letra
      (Character.isLetter: letras acentuadas valem; hífen, apóstrofo e ponto não) — "Nome tem
      caracteres inválidos.";
    - parte igual a ESPOLIO ou ESPÓLIO.
Três letras iguais seguidas só geram aviso no programa (severidade 2) e não são conferidas aqui.
Confirmado no programa em 18/11/2026: o nome "MAE TESTE - NOVA" gerou a pendência "Nome tem
caracteres inválidos" na ficha Dependentes.
"""

MAXIMO_PARTES = 15

def erro_nome_pessoa(nome: str) -> str | None:
    """Mensagem do problema (sem repetir o nome) ou None se o programa aceita o nome."""
    partes = nome.split()
    if len(partes) > MAXIMO_PARTES:
        return f"tem {len(partes)} partes; o máximo é {MAXIMO_PARTES}"
    for parte in partes:
        if any(c.isdigit() for c in parte):
            return "não pode ter números"
        if not all(c.isalpha() for c in parte):
            return "só letras e espaços (o programa recusa hífen, apóstrofo, ponto e outros sinais)"
        if parte.upper() in ("ESPOLIO", "ESPÓLIO"):
            return "informe o nome sem a palavra ESPÓLIO"
    return None
