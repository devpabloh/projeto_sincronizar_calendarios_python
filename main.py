import argparse
import sys
import os

# Adiciona o diretório do projeto ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.synchronizer import CalendarSynchronizer
from src.utils.logger import logger

def main():
    """Função principal que inicia a sincronização de calendários."""
    parser = argparse.ArgumentParser(description='Sincronizador de Calendários Gmail-Outlook')
    
    parser.add_argument(
        '--once', 
        action='store_true',
        help='Executa a sincronização apenas uma vez e encerra'
    )
    
    args = parser.parse_args()
    
    try:
        synchronizer = CalendarSynchronizer()
        
        if args.once:
            logger.info("Executando sincronização única")
            synchronizer.synchronize()
        else:
            logger.info("Iniciando sincronização contínua")
            synchronizer.run_continuous()
    
    except Exception as e:
        logger.error(f"Erro durante a execução: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())