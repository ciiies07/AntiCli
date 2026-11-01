"""
Wrapper de compatibilidad para AntiCli.
Permite ejecutar `python pi_antigravity.py` manteniendo compatibilidad
completa hacia atrás con `anticli.py`.
"""
import sys
import asyncio
from anticli import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
