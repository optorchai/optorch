import logging
import hashlib


class ContextFormatter(logging.Formatter):
    """Format logs with colored component, dim timestamp, bold logger name
    
    Captures: level (colored), component (colored), timestamp (dim), session_id, phase, logger (bold), message
    Colors dynamically assigned to components based on hash
    """
    
    LEVEL_COLORS = {
        'DEBUG': '\033[36m',      # cyan
        'INFO': '\033[32m',       # green
        'WARNING': '\033[33m',    # yellow
        'ERROR': '\033[31m',      # red
        'CRITICAL': '\033[35m',   # magenta
    }
    
    COMPONENT_PALETTE = [
        '\033[38;5;33m',   # blue
        '\033[38;5;39m',   # bright blue
        '\033[38;5;45m',   # cyan
        '\033[38;5;51m',   # bright cyan
        '\033[38;5;57m',   # purple
        '\033[38;5;63m',   # bright purple
        '\033[38;5;69m',   # slate
        '\033[38;5;75m',   # sky blue
        '\033[38;5;81m',   # light blue
        '\033[38;5;87m',   # cyan-ish
        '\033[38;5;99m',   # purple-ish
        '\033[38;5;105m',  # blue-purple
        '\033[38;5;111m',  # cornflower
        '\033[38;5;117m',  # light cyan
        '\033[38;5;141m',  # purple
        '\033[38;5;147m',  # lilac
    ]
    
    RESET = '\033[0m'
    DIM = '\033[2m'        # dim/faint for timestamp
    GRAY = '\033[2;1;38;5;214m'  # dim bold orangy yellow for logger name
    GREEN = '\033[1;32m'   # bold green for session_id
    
    DEFAULT_FORMAT = "%(levelname)s %(component)s%(asctime)s %(name)s %(message)s"
    
    def __init__(self, *args, use_color=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_color = use_color
        self._component_colors = {}
    
    def _get_component_color(self, component: str) -> str:
        """Get consistent color for component based on hash"""
        if component not in self._component_colors:
            hash_val = int(hashlib.md5(component.encode()).hexdigest(), 16)
            idx = hash_val % len(self.COMPONENT_PALETTE)
            self._component_colors[component] = self.COMPONENT_PALETTE[idx]
        return self._component_colors[component]
    
    def format(self, record: logging.LogRecord) -> str:
        component = getattr(record, 'component', None)
        if not component:
            parts = record.name.split('.')
            component = "optorch" if "optorch" in record.name else (parts[0] if parts else "optorch")
        
        if self.use_color:
            level_color = self.LEVEL_COLORS.get(record.levelname, '')
            padded_level = record.levelname.ljust(9)
            record.levelname = f"{level_color}{padded_level}{self.RESET}"
            
            component_color = self._get_component_color(component)
            bracket_str = f"{component_color}[{component}]{self.RESET}"
            visual_width = len(component) + 2
            spaces_needed = max(0, 14 - visual_width)
            record.component = bracket_str + (" " * spaces_needed) + " "  # type: ignore[attr-defined]
            
            record.name = f"{self.GRAY}{record.name}{self.RESET}"
        else:
            padded_level = record.levelname.ljust(8)
            record.levelname = padded_level
            visual_width = len(component) + 2
            spaces_needed = max(0, 14 - visual_width)
            record.component = f"[{component}]" + (" " * spaces_needed) + " "  # type: ignore[attr-defined]
        
        fmt = self._fmt or self.DEFAULT_FORMAT
        base_msg = super().format(record)
        
        if self.use_color:
            ts = self.formatTime(record, self.datefmt)
            base_msg = base_msg.replace(ts, f"{self.DIM}{ts}{self.RESET}", 1)
            
            session_id = getattr(record, 'session_id', None)
            if session_id:
                formatted_session = f" {self.GREEN}[{session_id}]{self.RESET}"
                base_msg = base_msg.replace(f"{self.DIM}{ts}{self.RESET}", f"{self.DIM}{ts}{self.RESET}{formatted_session}", 1)
        
        parts = [base_msg]
        session_id = getattr(record, 'session_id', None)
        if session_id and not self.use_color:
            parts.append(f"[{session_id}]")
        phase = getattr(record, 'phase', None)
        if phase:
            parts.append(f"[{phase}]")
        
        return " ".join(parts) if len(parts) > 1 else base_msg
