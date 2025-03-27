import sys # sys é utilizado para manipular o fluxo de entrada e saída de dados, como o console.
from loguru import logger # loguru é uma biblioteca de logging que fornece uma interface simples e poderosa para registrar mensagens de log.

from ..config.settings import config # configurações do projeto

logger.remove() # remove todos os handlers existentes do logger.

# Adiciona um novo handler ao logger.
# O handler é responsável por enviar as mensagens de log para o destino especificado.
logger.add(
    sys.stderr,
    level=config.sync.log_level,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

)

logger.add(
    "sync_calendar_log",
    rotation="10 MB",
    retention="1 week",
    level=config.sync.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)