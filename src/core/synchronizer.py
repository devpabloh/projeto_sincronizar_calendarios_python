import json
import os
import datetime
import time
from typing import Dict, List, Set, Tuple
import pytz
from ..adapters.gmail_adapter import GmailAdapter
from ..adapters.outlook_adapter import OutlookAdapter
from ..core.calendar_event import CalendarEvent
from ..config.settings import config
from ..utils.logger import logger

class CalendarSynchronizer:
    """Classe responsável por sincronizar eventos entre Gmail e Outlook."""
    
    def __init__(self):
        self.gmail_adapter = GmailAdapter()
        self.outlook_adapter = OutlookAdapter()
        self.last_sync_file = config.sync.last_sync_file
        self.last_sync_time = self._load_last_sync_time()
        self.sync_interval = config.sync.sync_interval_minutes
    
    def _load_last_sync_time(self) -> datetime.datetime:
        """Carrega o timestamp da última sincronização."""
        if os.path.exists(self.last_sync_file):
            try:
                with open(self.last_sync_file, 'r') as f:
                    data = json.load(f)
                    return datetime.datetime.fromisoformat(data.get('last_sync', ''))
            except Exception as e:
                logger.error(f"Erro ao carregar timestamp da última sincronização: {e}")
        
        # Se o arquivo não existir ou ocorrer um erro, retorna uma data no passado
        return datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=30)
    
    def _save_last_sync_time(self):
        """Salva o timestamp da sincronização atual."""
        now = datetime.datetime.now(pytz.UTC)
        with open(self.last_sync_file, 'w') as f:
            json.dump({'last_sync': now.isoformat()}, f)
        self.last_sync_time = now
    
    def _get_event_fingerprint(self, event: CalendarEvent) -> str:
        """Gera uma impressão digital única para um evento."""
        # Cria uma string que representa as propriedades essenciais do evento
        # para comparação e detecção de alterações
        fingerprint = (
            f"{event.summary}|"
            f"{event.description or ''}|"
            f"{event.location or ''}|"
            f"{event.start_time.isoformat()}|"
            f"{event.end_time.isoformat()}|"
            f"{event.is_all_day}|"
            f"{event.status}"
        )
        return fingerprint
    
    def _compare_events(self, gmail_events: List[CalendarEvent], 
                       outlook_events: List[CalendarEvent]) -> Tuple[Dict, Dict, Dict, Dict]:
        """
        Compara eventos entre Gmail e Outlook para determinar quais precisam ser sincronizados.
        
        Retorna:
            - eventos para criar no Gmail
            - eventos para criar no Outlook
            - eventos para atualizar no Gmail
            - eventos para atualizar no Outlook
        """
        # Mapeia eventos por ID para facilitar a comparação
        gmail_events_by_id = {event.source_id: event for event in gmail_events}
        outlook_events_by_id = {event.source_id: event for event in outlook_events}
        
        # Mapeia eventos por fingerprint para detectar duplicatas
        gmail_fingerprints = {self._get_event_fingerprint(event): event for event in gmail_events}
        outlook_fingerprints = {self._get_event_fingerprint(event): event for event in outlook_events}
        
        # Eventos para criar no Gmail (existem no Outlook mas não no Gmail)
        create_in_gmail = {}
        # Eventos para criar no Outlook (existem no Gmail mas não no Outlook)
        create_in_outlook = {}
        # Eventos para atualizar no Gmail (existem em ambos mas foram modificados no Outlook)
        update_in_gmail = {}
        # Eventos para atualizar no Outlook (existem em ambos mas foram modificados no Gmail)
        update_in_outlook = {}
        
        # Verifica eventos que existem no Outlook mas não no Gmail
        for outlook_id, outlook_event in outlook_events_by_id.items():
            outlook_fingerprint = self._get_event_fingerprint(outlook_event)
            
            # Se o fingerprint não existe no Gmail, precisamos criar o evento
            if outlook_fingerprint not in gmail_fingerprints:
                # Verifica se o evento já tem um ID correspondente no Gmail
                # (pode ter sido modificado, então o fingerprint mudou)
                if outlook_event.source_id not in gmail_events_by_id:
                    create_in_gmail[outlook_id] = outlook_event
        
        # Verifica eventos que existem no Gmail mas não no Outlook
        for gmail_id, gmail_event in gmail_events_by_id.items():
            gmail_fingerprint = self._get_event_fingerprint(gmail_event)
            
            # Se o fingerprint não existe no Outlook, precisamos criar o evento
            if gmail_fingerprint not in outlook_fingerprints:
                # Verifica se o evento já tem um ID correspondente no Outlook
                # (pode ter sido modificado, então o fingerprint mudou)
                if gmail_event.source_id not in outlook_events_by_id:
                    create_in_outlook[gmail_id] = gmail_event
        
        # Verifica eventos que existem em ambos mas foram modificados
        for gmail_id, gmail_event in gmail_events_by_id.items():
            # Se o evento existe no Outlook
            if gmail_id in outlook_events_by_id:
                outlook_event = outlook_events_by_id[gmail_id]
                gmail_fingerprint = self._get_event_fingerprint(gmail_event)
                outlook_fingerprint = self._get_event_fingerprint(outlook_event)
                
                # Se os fingerprints são diferentes, um dos eventos foi modificado
                if gmail_fingerprint != outlook_fingerprint:
                    # Verifica qual evento foi atualizado mais recentemente
                    if gmail_event.updated > outlook_event.updated:
                        # Gmail é mais recente, atualiza no Outlook
                        update_in_outlook[gmail_id] = gmail_event
                    else:
                        # Outlook é mais recente, atualiza no Gmail
                        update_in_gmail[outlook_id] = outlook_event
        
        return create_in_gmail, create_in_outlook, update_in_gmail, update_in_outlook
    
    def _find_deleted_events(self, current_events: List[CalendarEvent], 
                           previous_events: List[CalendarEvent]) -> List[str]:
        """
        Identifica eventos que foram excluídos comparando listas atual e anterior.
        
        Retorna:
            - lista de IDs de eventos excluídos
        """
        current_ids = {event.source_id for event in current_events}
        previous_ids = {event.source_id for event in previous_events}
        
        # Eventos que existiam antes mas não existem mais
        deleted_ids = previous_ids - current_ids
        
        return list(deleted_ids)
    
    def synchronize(self):
        """Executa a sincronização entre os calendários do Gmail e Outlook."""
        logger.info("Iniciando sincronização de calendários")
        
        # Define o intervalo de tempo para buscar eventos
        time_min = self.last_sync_time - datetime.timedelta(days=1)  # Busca eventos desde 1 dia antes da última sincronização
        time_max = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=90)  # Até 90 dias no futuro
        
        # Obtém eventos de ambos os calendários
        gmail_events = self.gmail_adapter.get_events(time_min, time_max)
        outlook_events = self.outlook_adapter.get_events(time_min, time_max)
        
        # Compara eventos para determinar quais precisam ser sincronizados
        create_in_gmail, create_in_outlook, update_in_gmail, update_in_outlook = self._compare_events(
            gmail_events, outlook_events
        )
        
        # Processa criações no Gmail
        for event_id, event in create_in_gmail.items():
            try:
                # Cria uma cópia do evento para o Gmail
                gmail_event = event.copy()
                gmail_event.source = 'gmail'
                
                # Cria o evento no Gmail
                self.gmail_adapter.create_event(gmail_event)
                logger.info(f"Evento criado no Gmail: {event.summary}")
            except Exception as e:
                logger.error(f"Erro ao criar evento no Gmail: {e}")
        
        # Processa criações no Outlook
        for event_id, event in create_in_outlook.items():
            try:
                # Cria uma cópia do evento para o Outlook
                outlook_event = event.copy()
                outlook_event.source = 'outlook'
                
                # Cria o evento no Outlook
                self.outlook_adapter.create_event(outlook_event)
                logger.info(f"Evento criado no Outlook: {event.summary}")
            except Exception as e:
                logger.error(f"Erro ao criar evento no Outlook: {e}")
        
        # Processa atualizações no Gmail
        for event_id, event in update_in_gmail.items():
            try:
                # Cria uma cópia do evento para o Gmail
                gmail_event = event.copy()
                gmail_event.source = 'gmail'
                
                # Atualiza o evento no Gmail
                self.gmail_adapter.update_event(gmail_event)
                logger.info(f"Evento atualizado no Gmail: {event.summary}")
            except Exception as e:
                logger.error(f"Erro ao atualizar evento no Gmail: {e}")
        
        # Processa atualizações no Outlook
        for event_id, event in update_in_outlook.items():
            try:
                # Cria uma cópia do evento para o Outlook
                outlook_event = event.copy()
                outlook_event.source = 'outlook'
                
                # Atualiza o evento no Outlook
                self.outlook_adapter.update_event(outlook_event)
                logger.info(f"Evento atualizado no Outlook: {event.summary}")
            except Exception as e:
                logger.error(f"Erro ao atualizar evento no Outlook: {e}")
        
        # Processa exclusões (eventos que existiam na última sincronização mas não existem mais)
        # Nota: Esta é uma implementação simplificada. Uma implementação mais robusta
        # armazenaria os IDs de eventos da última sincronização para comparação.
        
        # Salva o timestamp da sincronização atual
        self._save_last_sync_time()
        
        logger.info(f"Sincronização concluída. Próxima sincronização em {self.sync_interval} minutos")
    
    def run_continuous(self):
        """Executa a sincronização continuamente com o intervalo configurado."""
        logger.info(f"Iniciando sincronização contínua com intervalo de {self.sync_interval} minutos")
        
        try:
            while True:
                self.synchronize()
                # Aguarda o intervalo configurado antes da próxima sincronização
                time.sleep(self.sync_interval * 60)
        except KeyboardInterrupt:
            logger.info("Sincronização interrompida pelo usuário")
        except Exception as e:
            logger.error(f"Erro durante a sincronização contínua: {e}")
            raise