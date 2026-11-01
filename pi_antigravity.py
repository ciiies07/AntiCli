"""
Wrapper de compatibilidad para AntiCli.
Permite ejecutar `python pi_antigravity.py` o `python anticli.py` de forma indistinta.
"""
from anticli import run_cli

if __name__ == "__main__":
    run_cli()
