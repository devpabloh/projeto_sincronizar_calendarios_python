import os # utilizado para limpar o terminal
from dotenv import load_dotenv # utilizado para carregar as variaveis de ambiente
from pydantic import BaseModel # basemodel é uma classe que permite criar classes com tipos de dados

load_dotenv() # carregando as variáveis de ambiente

# configurando o Gmail
class GmailConfig(BaseModel):
    credentials_file: str = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file: str = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    scopes: list = ["https://www.googleapis.com/auth/calendar"]
    calendar_id: str = os.getenv("GMAIL_CALENDAR_ID", "primary")

# Configuração do Outlook
class OutlookConfig(BaseModel):
    client_id: str = os.getenv("OUTLOOK_CLIENT_ID", "")
    client_secret: str = os.getenv("OUTLOOK_CLIENT_SECRET", "")
    tenant_id: str = os.getenv("OUTLOOK_TENANT_ID", "")
    calendar_id: str = os.getenv("OUTLOOK_CALENDAR_ID", "")

# Configuração de sincronização
class SyncConfig(BaseModel):
    sync_interval_minutes: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "30"))
    last_sync_file: str = os.getenv("LAST_SYNC_FILE", "last_sync.json")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
# Classe principal de configuração
class config(BaseModel):
    gmail: GmailConfig = GmailConfig()
    outlook: OutlookConfig = OutlookConfig()
    sync: SyncConfig = SyncConfig()

# Criando uma instância global de configuração
config = config()