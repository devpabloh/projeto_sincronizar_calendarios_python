import os 
import datetime
from typing import List, Optional
import pytz # pytz é uma biblioteca que fornece suporte para fusos horários.
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from ..core.calendar_event import CalendarEvent
from ..config.settings import config
from ..utils.logger import logger

class GmailAdapter:
    """Adaptador para interagir com a API do Google Calendar."""

    def __init__(self):
        self.creds = None
        self.service = None
        self.calendar_id = config.gmail.calendar_id
        self.authenticate()

    def authenticate(self):
        """Autentica o usuário e obtém as credenciais do Google Calendar."""
        scopes = config.gmail.scopes
        creds = None

        if os.path.exists(config.gmail.token_file):
            creds = Credentials.from_authorized_user_info(
                eval(open(config.gmail.token_file, "r").read()),
                scopes
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.gmail.credentials_file, scopes)
                creds = flow.run_local_server(port=0)
            with open(config.gmail.token_file, 'w') as token:
                token.write(str(creds.to_json()))

        self.creds = creds
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("Autenticação bem-sucedida com o Google Calendar.")

def _convert_to_calendar_event(self, event) -> CalendarEvent:
        """Converte um evento do Google Calendar para o modelo CalendarEvent."""
        # Determina se é um evento de dia inteiro
        is_all_day = 'date' in event['start'] and 'date' in event['end']

        # processando datas
        if is_all_day:
            start_time = datetime.datetime.fromisoformat(event['start']['date'])
            end_time = datetime.datetime.fromisoformat(event['end']['date'])
        else: 
            start_time = datetime.datetime.fromisoformat(event['start'].get('dateTime', ''))
            end_time = datetime.datetime.fromisoformat(event['end'].get('dateTime', ''))


        attendees = None
        if 'attendees' in event:
            attendees = [
                {'email': attendee.get('email', ''), 
                'name': attendee.get('displayName', ''),
                'response_status': attendee.get('responseStatus', '')}
                for attendee in event['attendees']
            ]
        
        # Criando um objeto CalendarEvent
        return CalendarEvent(
            id=event['id'],
            summary=event.get('summary', 'Sem título'),
            description=event.get('description', None),
            location=event.get('location', None),
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            recurrence=event.get('recurrence', None),
            attendees=attendees,
            organizer=organizer,
            status=event.get('status', 'confirmed'),
            created=datetime.datetime.fromisoformat(event.get('created', datetime.datetime.now().isoformat())),
            updated=datetime.datetime.fromisoformat(event.get('updated', datetime.datetime.now().isoformat())),
            source='gmail',
            source_id=event['id']
        )

        def _convert_from_calendar_event(self, event: CalendarEvent) -> dict:
            """Converte um CalendarEvent para o formato do Google Calendar."""
        google_event = {
            'summary': event.summary,
            'status': event.status
        }
        
        if event.description:
            google_event['description'] = event.description
        
        if event.location:
            google_event['location'] = event.location
        
        # Define datas
        if event.is_all_day:
            start_date = event.start_time.date().isoformat()
            end_date = event.end_time.date().isoformat()
            google_event['start'] = {'date': start_date}
            google_event['end'] = {'date': end_date}
        else:
            start_datetime = event.start_time.isoformat()
            end_datetime = event.end_time.isoformat()
            google_event['start'] = {'dateTime': start_datetime, 'timeZone': 'UTC'}
            google_event['end'] = {'dateTime': end_datetime, 'timeZone': 'UTC'}
        
        # Adiciona recorrência se existir
        if event.recurrence:
            google_event['recurrence'] = event.recurrence
        
        # Adiciona participantes se existirem
        if event.attendees:
            google_event['attendees'] = [
                {
                    'email': attendee.get('email', ''),
                    'displayName': attendee.get('name', ''),
                    'responseStatus': attendee.get('response_status', 'needsAction')
                }
                for attendee in event.attendees
            ]
        
        return google_event

        def get_events(self, time_min: Optional[datetime.datetime] = None, 
                time_max: Optional[datetime.datetime] = None) -> List[CalendarEvent]:
            """Obtém eventos do Google Calendar."""
        if not time_min:
            time_min = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=30)
        if not time_max:
            time_max = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=90)
        
        # Formata as datas para o formato ISO
        time_min_str = time_min.isoformat()
        time_max_str = time_max.isoformat()
        
        logger.info(f"Buscando eventos do Gmail entre {time_min_str} e {time_max_str}")
        
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min_str,
            timeMax=time_max_str,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        calendar_events = [self._convert_to_calendar_event(event) for event in events]
        
        logger.info(f"Encontrados {len(calendar_events)} eventos no Gmail")
        return calendar_events

        def create_event(self, event: CalendarEvent) -> CalendarEvent:
            """Cria um novo evento no Google Calendar."""
            google_event = self._convert_from_calendar_event(event)
            
            logger.info(f"Criando evento no Gmail: {event.summary}")
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=google_event
            ).execute()
            
            # Atualiza o ID do evento com o ID retornado pelo Google
            event.id = created_event['id']
            event.source_id = created_event['id']
            
            logger.info(f"Evento criado com sucesso no Gmail: {event.id}")
        return event

        def update_event(self, event: CalendarEvent) -> CalendarEvent:
            """Atualiza um evento existente no Google Calendar."""
            google_event = self._convert_from_calendar_event(event)

            logger.info(f"Atualizando evento no Gmail: {event.summary} (ID: {event.source_id})")

            update_event = self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event.source_id,
                body=google_event
            ).execute()

            logger.info(f"Evento atualizado com sucesso no Gmail: {event.source_id}")
            return event
        
        def delete_event(self, event_id: str) -> bool:
            """Deleta um evento do Google Calendar."""
            logger.info(f"Deletando evento no Gmail: {event_id}")

            try: 
                self.service.events().delete(
                    calendarId=self.calendar_id,
                    eventId=event_id
                ).execute()
                logger.info(f"Evento deletado com sucesso no Gmail: {event_id}")
                return True
            except Exception as e:
                logger.error(f"Erro ao deletar evento no Gmail: {e}")
                return False
