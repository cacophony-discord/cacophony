from .commands import on_remind
from .coroutines import reminder


commands = {
    'remind': [on_remind]
}

coroutines = [reminder]
