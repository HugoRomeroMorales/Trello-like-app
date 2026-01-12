import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class User:
    username: str
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __repr__(self):
        return f"<User: {self.username}>"

@dataclass
class Label:
    name: str
    color: str  
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Comment:
    author: User
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Tarjeta:
    title: str
    description: str = ""
    assignees: List[User] = field(default_factory=list)
    labels: List[Label] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    due_date: Optional[datetime] = None
    is_archived: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def aniadirComentario(self, user: User, content: str):
        new_comment = Comment(author=user, content=content)
        self.comments.append(new_comment)
    
    def aniadiretiqueta(self, label: Label):
        if label not in self.labels:
            self.labels.append(label)

@dataclass
class TrelloLista:
    name: str
    cards: List[Tarjeta] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_card(self, tarjeta: Tarjeta):
        self.cards.append(tarjeta)
        
    def remove_card(self, Tarjeta_id: str):
        self.cards = [c for c in self.cards if c.id != card_id]

@dataclass
class Tablero:
    name: str
    owner: User
    lists: List[TrelloLista] = field(default_factory=list)
    members: List[User] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def add_list(self, trello_list: TrelloList):
        self.lists.append(trello_list)
        
    def get_card_count(self):
        return sum(len(l.cards) for l in self.lists)