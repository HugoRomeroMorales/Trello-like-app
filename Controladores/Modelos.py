import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class User:
    username: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def __repr__(self):
        return f"<User: {self.username}>"

@dataclass
class Tarjeta:
    titulo: str
    lista_id: str
    descripcion: str = ""
    posicion: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    # Runtime only fields (not in DB directly, but useful for UI)
    assignees: List[User] = field(default_factory=list) 

@dataclass
class TrelloLista:
    titulo: str
    tablero_id: str
    posicion: int = 0
    cards: List[Tarjeta] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def add_card(self, tarjeta: Tarjeta):
        self.cards.append(tarjeta)
        
    def remove_card(self, tarjeta_id: str):
        self.cards = [c for c in self.cards if c.id != tarjeta_id]

@dataclass
class Tablero:
    titulo: str
    es_publico: bool = False
    lists: List[TrelloLista] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def add_list(self, trello_list: TrelloLista):
        self.lists.append(trello_list)
    
    def remove_list(self, list_id: str):
        self.lists = [l for l in self.lists if l.id != list_id]
        
    def get_card_count(self):
        return sum(len(l.cards) for l in self.lists)
