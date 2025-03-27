from datetime import datetime # datatime é utilizado para manipular datas e horas.
from typing import Optional, List, Dict, Any # typing é utilizado para definir tipos de dados.
from pydantic import BaseModel, Field # pydantic é utilizado para definir modelos de dados.

class CalendarEvent(BaseModel):
    """
    Modelo para representar eventos de calendário independente da plataforma.
    """

    id: str
    summary: str
    description: Optional[str] = None
    localization: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    recurrence: Optional[List[str]] = None
    attendees: Optional[List[Dict[str, str]]] = None
    organizer: Optional[Dict[str, str]] = None
    status: str = "confirmed"
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    source: str  
    source_id: str  

    class Config: 
        arbitrary_types_allowed = True
