import os # os é utilizado para manipular o sistema operacional.
import json # json é utilizado para manipular arquivos JSON.
import datetime # datetime é utilizado para manipular datas e horas.
from typing import List, Optional # List e Optional são utilizados para definir tipos de retorno.
import pytz # pytz é utilizado para manipular fusos horários.
from O365 import Account, FileSystemTokenBackend # Account e FileSystemTokenBackend são utilizados para autenticar no Microsoft 365.
from O365.calendar import Event as O365Event # 0365Event é utilizado para manipular eventos no Microsoft 365.
from ..core.calendar_event import CalendarEvent # CalendarEvent é utilizado para manipular eventos no calendário.
from ..config.settings import config # config é utilizado para acessar as configurações do sistema. 
from ..utils.logger import logger # ..utils.logger é utilizado para acessar o logger do sistema.

class OutlookAdapter:
    """Adaptador para interagir com a API do Outlook Calendar."""

    def __init__(self):
        """Inicializa o adaptador."""
        self.account = None
        self.calendar = None
        self.authenticate()

    def authenticate(self):
        """Autentica no Outlook Calendar."""
        client_id = config.outlook.client_id
        client_secret = config.outlook.client_secret

        # configurando o backend do token
        token_backend = FileSystemTokenBackend(token_path='.', token_filename='o365_token.txt')

        # Cria a conta
        self.account = Account((client_id, client_secret), token_backend=token_backend)

        
        if not self.account.is_authenticated:
            # Solicitando permissões para calendário
            scopes = ['basic', 'calendar']
            if self.account.authenticate(scopes=scopes):
                logger.info("Autenticado com sucesso na API do Outlook Calendar")
            else:
                logger.error("Falha na autenticação na API do Outlook Calendar")
                raise Exception("Falha na autenticação com a API do Outlook Calendar")

        # Obtendo o calendário
        schedule = self.account.schedule()
        calendar_id = config.outlook.calendar_id

        if calendar_id:
            self.calendar = schedule.get_calendar(calendar_id=calendar_id)
        else: 
            self.calendar = schedule.get_default_calendar()
        
            logger.info(f"Usando calendário: {self.calendar.name}")
    
    def _convert_to_calendar_event(self, event: O365Event) -> CalendarEvent:
        """Converte um evento do Outlook para o modelo CalendarEvent."""

        # Determina se é um evento de dia inteiro
        is_all_day = event.is_all_day
        
        # Processa datas
        start_time = event.start
        end_time = event.end
        
        # Processa participantes
        attendees = None
        if event.attendees:
            attendees = [
                {'email': attendee.address, 
                'name': attendee.name,
                'response_status': attendee.response_status}
                for attendee in event.attendees
            ]
        
        # Processa organizador
        organizer = None
        if event.organizer:
            organizer = {
                'email': event.organizer.address,
                'name': event.organizer.name
            }
        
        # Processa recorrência
        recurrence = None
        if event.recurrence:
            recurrence = [event.recurrence.serialize()]
        
        # Cria o objeto CalendarEvent
        return CalendarEvent(
            id=event.object_id,
            summary=event.subject,
            description=event.body,
            location=event.location.get('displayName') if event.location else None,
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            recurrence=recurrence,
            attendees=attendees,
            organizer=organizer,
            status='confirmed' if not event.is_cancelled else 'cancelled',
            created=event.created,
            updated=event.modified,
            source='outlook',
            source_id=event.object_id
        )

    def _convert_from_calendar_event(self, event: CalendarEvent) -> O365Event:
        """Converte um CalendarEvent para o formato do Outlook Calendar."""
        outlook_event = self.calendar.new_event()
        outlook_event.subject = event.summary
        
        if event.description:
            outlook_event.body = event.description
        
        if event.location:
            outlook_event.location = {'displayName': event.location}
        
        # Define datas
        outlook_event.start = event.start_time
        outlook_event.end = event.end_time
        outlook_event.is_all_day = event.is_all_day
        
        # Adiciona participantes se existirem
        if event.attendees:
            for attendee in event.attendees:
                outlook_event.attendees.add(attendee.get('email'), attendee.get('name', ''))
        
    return outlook_event
    
    def get_events(self, time_min: Optional[datetime.datetime] = None, 
                time_max: Optional[datetime.datetime] = None) -> List[CalendarEvent]:
        """Obtém eventos do Outlook Calendar."""
        if not time_min:
            time_min = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=30)
        if not time_max:
            time_max = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=90)
        
        logger.info(f"Buscando eventos do Outlook entre {time_min.isoformat()} e {time_max.isoformat()}")
        
        # Consulta eventos no intervalo especificado
        q = self.calendar.new_query('start').greater_equal(time_min)
        q.chain('and').on_attribute('end').less_equal(time_max)
        
        events = list(self.calendar.get_events(query=q, include_recurring=True))
        calendar_events = [self._convert_to_calendar_event(event) for event in events]
        
        logger.info(f"Encontrados {len(calendar_events)} eventos no Outlook")
    return calendar_events
        
    def create_event(self, event: CalendarEvent) -> CalendarEvent:
            """Cria um novo evento no Outlook Calendar."""
            outlook_event = self._convert_from_calendar_event(event)
        
            logger.info(f"Criando evento no Outlook: {event.summary}")
        
            if outlook_event.save():
                # Atualiza o ID do evento com o ID retornado pelo Outlook
                event.id = outlook_event.object_id
                event.source_id = outlook_event.object_id
                logger.info(f"Evento criado com sucesso no Outlook: {event.id}")
            else:
                logger.error("Falha ao criar evento no Outlook")
                raise Exception("Falha ao criar evento no Outlook")
        
    return event

    def update_event(self, event: CalendarEvent) -> CalendarEvent:
        """Atualiza um evento existente no Outlook Calendar."""
        # Obtém o evento existente
        outlook_event = self.calendar.get_event(event.source_id)
        
        if not outlook_event:
            logger.error(f"Evento não encontrado no Outlook: {event.source_id}")
            raise Exception(f"Evento não encontrado no Outlook: {event.source_id}")
        
        logger.info(f"Atualizando evento no Outlook: {event.summary} (ID: {event.source_id})")
        
        # Atualiza os campos
        outlook_event.subject = event.summary
        
        if event.description:
            outlook_event.body = event.description
        
        if event.location:
            outlook_event.location = {'displayName': event.location}
        
        # Define datas
        outlook_event.start = event.start_time
        outlook_event.end = event.end_time
        outlook_event.is_all_day = event.is_all_day
        
        # Salva as alterações
        if outlook_event.save():
            logger.info(f"Evento atualizado com sucesso no Outlook: {event.source_id}")
        else:
            logger.error("Falha ao atualizar evento no Outlook")
            raise Exception("Falha ao atualizar evento no Outlook")
        
    return event

    def delete_event(self, event_id: str) -> bool:
        """Exclui um evento do Outlook Calendar."""
        logger.info(f"Excluindo evento do Outlook: {event_id}")
        
        # Obtém o evento existente
        outlook_event = self.calendar.get_event(event_id)
        
        if not outlook_event:
            logger.warning(f"Evento não encontrado no Outlook: {event_id}")
            return False
        
        # Exclui o evento
        if outlook_event.delete():
            logger.info(f"Evento excluído com sucesso do Outlook: {event_id}")
            return True
        else:
            logger.error(f"Falha ao excluir evento do Outlook: {event_id}")
    return False